#!/usr/bin/env python
"""Phase 2 GraphRAG Batch Index Orchestrator (skeleton)

Responsibilities:
- Prepare staging output directory (timestamped)
- Invoke GraphRAG indexing CLI (placeholder command for now)
- On success, call import_graphrag_artifacts for new artifacts
- Update graphrag_service.metrics (last_index_run_at, duration, status)

NOTE: This is a scaffold; actual GraphRAG CLI invocation will be wired once dependency added.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
import json
import os
import fcntl
from collections import defaultdict

from app.core.config import settings
from app.core.graphrag_service import graphrag_service
from app.core import database as db

SCRIPT_DIR = Path(__file__).parent


def _extract_text_from_file(fp: Path, max_chars: int = 120_000) -> str:
    """Best-effort text extraction for .txt/.md/.pdf files.
    - .txt/.md: read as UTF-8 with ignore errors
    - .pdf: try pdfplumber first, then PyPDF2
    Returns at most max_chars characters.
    """
    try:
        suffix = fp.suffix.lower()
        if suffix in {".txt", ".md"}:
            return fp.read_text(errors="ignore")[:max_chars]
        if suffix == ".pdf":
            text = ""
            # Attempt with pdfplumber (handles layout reasonably)
            try:
                import pdfplumber  # type: ignore
                with pdfplumber.open(str(fp)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        try:
                            txt = page.extract_text() or ""
                        except Exception:
                            txt = ""
                        if txt:
                            text += txt + "\n"
                        if len(text) >= max_chars or i >= 150:  # cap pages to avoid long runs
                            break
                if text.strip():
                    return text[:max_chars]
            except Exception:
                pass
            # Fallback to PyPDF2
            try:
                import PyPDF2  # type: ignore
                with open(fp, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for i, page in enumerate(reader.pages):
                        try:
                            text += page.extract_text() or ""
                            text += "\n"
                        except Exception:
                            continue
                        if len(text) >= max_chars or i >= 150:
                            break
                return text[:max_chars]
            except Exception:
                return ""
        # Unknown type: try bytes decode
        return fp.read_text(errors="ignore")[:max_chars]
    except Exception:
        return ""


def run_dummy_pipeline(output_dir: Path):
    # Placeholder: create minimal artifact CSVs for testing orchestration
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'entities.csv').write_text('entity_id,name,type,description\neA,Alpha,Concept,Alpha desc')
    (output_dir / 'relationships.csv').write_text('relationship_id,src_id,dst_id,relationship_type,weight\nr1,eA,eA,RELATED_TO,1.0')
    (output_dir / 'communities.csv').write_text('community_id,entity_id\nc1,eA')
    (output_dir / 'community_reports.csv').write_text('community_id,report_title,report_summary\nc1,Community C1,Synthetic summary')


def run_gemini_fallback(input_dir: Path, output_dir: Path):
    """Generate lightweight GraphRAG-like artifacts using existing Gemini extraction.

    This bypasses the official GraphRAG pipeline (which currently expects OpenAI) so we can
    still exercise import + visualization end-to-end.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    from app.core.graphrag_service import graphrag_service  # lazy import
    import asyncio
    try:
        import networkx as nx  # type: ignore
    except Exception:
        nx = None  # type: ignore

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    entity_map: dict[str, dict] = {}
    name_to_id: dict[str, str] = {}
    rel_weights: defaultdict[tuple[str, str, str], float] = defaultdict(float)

    files = [p for p in input_dir.rglob('*') if p.suffix.lower() in {'.txt', '.md', '.pdf'} and p.is_file()]
    for fp in files:
        try:
            text = _extract_text_from_file(fp, max_chars=120_000)
        except Exception:
            continue
        try:
            result = loop.run_until_complete(graphrag_service.extract_entities_and_relations(text))  # type: ignore
        except Exception:
            continue
        tmp_id_to_name: dict[str, str] = {}
        # Track labels per canonical entity for domain relations
        canonical_labels: dict[str, str] = {}
        for n in result.nodes:
            key = n['name'].strip().lower()
            if not key:
                continue
            if key not in name_to_id:
                ent_id = n.get('id') or key.replace(' ', '_')
                name_to_id[key] = ent_id
                entity_map[ent_id] = {
                    'entity_id': ent_id,
                    'name': n['name'],
                    'type': n.get('label', 'Entity') or 'Entity',
                    'description': n.get('properties', {}).get('description', ''),
                }
            canonical_labels[name_to_id[key]] = (n.get('label') or 'Entity')
            tmp_id_to_name[n.get('id')] = key
        for r in result.edges:
            # map ephemeral extraction IDs back to canonical entity ids
            src_key = tmp_id_to_name.get(r.get('source_id'))
            dst_key = tmp_id_to_name.get(r.get('target_id'))
            if not src_key or not dst_key:
                continue
            src_id = name_to_id.get(src_key)
            dst_id = name_to_id.get(dst_key)
            if not src_id or not dst_id:
                continue
            rel_type = r.get('relation', 'RELATED_TO')
            rel_weights[(src_id, dst_id, rel_type)] += 1.0
        # Derived domain relations (Phase 4 initial): ROLE_AT and USES_TECH based on labels in same file
        try:
            role_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'role','title','position'}]
            org_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'organization','company','org'}]
            tech_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'technology','tool','framework'}]
            for r_id in role_nodes:
                for o_id in org_nodes:
                    rel_weights[(r_id, o_id, 'ROLE_AT')] += 0.5
            for holder in role_nodes + org_nodes:
                for t_id in tech_nodes:
                    rel_weights[(holder, t_id, 'USES_TECH')] += 0.4
        except Exception:
            pass

    # Write entities
    with (output_dir / 'entities.csv').open('w') as f:
        f.write('entity_id,name,type,description\n')
        for ent in entity_map.values():
            desc = (ent['description'] or '').replace('\n', ' ').replace('\r', ' ')
            f.write(f"{ent['entity_id']},{ent['name'].replace(',', ' ')},{ent['type']},{desc}\n")

    # Relationships + graph build
    if nx:
        G = nx.Graph()
        for eid in entity_map:
            G.add_node(eid)
    with (output_dir / 'relationships.csv').open('w') as f:
        f.write('relationship_id,src_id,dst_id,relationship_type,weight\n')
        for (s, d, rel_type), w in rel_weights.items():
            rid = f"r_{abs(hash((s,d,rel_type)))%10**10}"
            f.write(f"{rid},{s},{d},{rel_type},{w}\n")
            if nx:
                G.add_edge(s, d)

    # Communities via connected components (or singletons)
    communities: list[list[str]] = []
    if nx:
        try:
            communities = [list(c) for c in nx.connected_components(G)]  # type: ignore
        except Exception:
            pass
    if not communities:
        communities = [[eid] for eid in entity_map]

    with (output_dir / 'communities.csv').open('w') as f:
        f.write('community_id,entity_id\n')
        for i, comm in enumerate(communities, start=1):
            cid = f'c{i}'
            for eid in comm:
                f.write(f'{cid},{eid}\n')

    with (output_dir / 'community_reports.csv').open('w') as f:
        f.write('community_id,report_title,report_summary\n')
        for i, comm in enumerate(communities, start=1):
            cid = f'c{i}'
            names = [entity_map[e]['name'] for e in comm][:12]
            title = f'Community {i}'
            summary = 'Entities: ' + ', '.join(names)
            f.write(f"{cid},{title},{summary}\n")

    return {
        'entities': len(entity_map),
        'relationships': len(rel_weights),
        'communities': len(communities),
    }


def run_gemini_index(input_dir: Path, output_dir: Path, doc_ids: list[str]):
    """Selective Gemini-based indexing for a subset of raw documents (delta mode).

    Writes the same artifact CSV files but only for provided doc_ids (matching filename stems).
    Falls back to full run_gemini_fallback if no matching files found.
    """
    # Normalize ids (stems)
    id_set = {d.strip() for d in doc_ids if d.strip()}
    files = [p for p in input_dir.rglob('*') if p.suffix.lower() in {'.txt', '.md', '.pdf'} and p.is_file()]
    target_files = [p for p in files if p.stem in id_set]
    if not target_files:
        # Fallback to full
        return run_gemini_fallback(input_dir, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    from app.core.graphrag_service import graphrag_service  # lazy import
    import asyncio, uuid
    from collections import defaultdict
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    entity_map: dict[str, dict] = {}
    name_to_id: dict[str, str] = {}
    rel_weights: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    for fp in target_files:
        try:
            text = _extract_text_from_file(fp, max_chars=120_000)
        except Exception:
            continue
        try:
            result = loop.run_until_complete(graphrag_service.extract_entities_and_relations(text))  # type: ignore
        except Exception:
            continue
        tmp_id_to_name: dict[str, str] = {}
        canonical_labels: dict[str, str] = {}
        for n in result.nodes:
            key = n['name'].strip().lower()
            if not key:
                continue
            if key not in name_to_id:
                ent_id = n.get('id') or key.replace(' ', '_')
                name_to_id[key] = ent_id
                entity_map[ent_id] = {
                    'entity_id': ent_id,
                    'name': n['name'],
                    'type': n.get('label', 'Entity') or 'Entity',
                    'description': n.get('properties', {}).get('description', ''),
                }
            canonical_labels[name_to_id[key]] = (n.get('label') or 'Entity')
            tmp_id_to_name[n.get('id')] = key
        for r in result.edges:
            src_key = tmp_id_to_name.get(r.get('source_id'))
            dst_key = tmp_id_to_name.get(r.get('target_id'))
            if not src_key or not dst_key:
                continue
            src_id = name_to_id.get(src_key)
            dst_id = name_to_id.get(dst_key)
            if not src_id or not dst_id:
                continue
            rel_type = r.get('relation', 'RELATED_TO')
            rel_weights[(src_id, dst_id, rel_type)] += 1.0
        # Derived domain relations (Phase 4 initial)
        try:
            role_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'role','title','position'}]
            org_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'organization','company','org'}]
            tech_nodes = [eid for eid, lab in canonical_labels.items() if str(lab).lower() in {'technology','tool','framework'}]
            for r_id in role_nodes:
                for o_id in org_nodes:
                    rel_weights[(r_id, o_id, 'ROLE_AT')] += 0.5
            for holder in role_nodes + org_nodes:
                for t_id in tech_nodes:
                    rel_weights[(holder, t_id, 'USES_TECH')] += 0.4
        except Exception:
            pass
    # Write artifacts (subset)
    (output_dir / 'entities.csv').write_text('entity_id,name,type,description\n')
    with (output_dir / 'entities.csv').open('a') as f:
        for ent in entity_map.values():
            desc = (ent['description'] or '').replace('\n', ' ').replace('\r', ' ')
            f.write(f"{ent['entity_id']},{ent['name'].replace(',', ' ')},{ent['type']},{desc}\n")
    with (output_dir / 'relationships.csv').open('w') as f:
        f.write('relationship_id,src_id,dst_id,relationship_type,weight\n')
        for (s,d,rel_type), w in rel_weights.items():
            rid = f"r_{abs(hash((s,d,rel_type)))%10**10}"
            f.write(f"{rid},{s},{d},{rel_type},{w}\n")
    # Communities: naive connected components using relation pairs
    import networkx as nx  # type: ignore
    G = nx.Graph()
    for eid in entity_map:
        G.add_node(eid)
    for (s,d,rel_type), w in rel_weights.items():
        G.add_edge(s,d)
    try:
        communities = [list(c) for c in nx.connected_components(G)]
    except Exception:
        communities = [[eid] for eid in entity_map]
    with (output_dir / 'communities.csv').open('w') as f:
        f.write('community_id,entity_id\n')
        for i, comm in enumerate(communities, start=1):
            cid = f'c{i}'
            for eid in comm:
                f.write(f'{cid},{eid}\n')
    with (output_dir / 'community_reports.csv').open('w') as f:
        f.write('community_id,report_title,report_summary\n')
        for i, comm in enumerate(communities, start=1):
            cid = f'c{i}'
            names = [entity_map[e]['name'] for e in comm][:12]
            title = f'Community {i}'
            summary = 'Entities: ' + ', '.join(names)
            f.write(f"{cid},{title},{summary}\n")
    return {
        'entities': len(entity_map),
        'relationships': len(rel_weights),
        'communities': len(communities),
        'delta_mode': True,
        'docs_processed': len(target_files),
    }


def _prune_old_runs(root: Path, keep: int = 5):
    runs = sorted([p for p in root.glob('run-*') if p.is_dir()], key=lambda p: p.name, reverse=True)
    for p in runs[keep:]:
        try:
            for child in p.glob('**/*'):
                if child.is_file():
                    child.unlink()
            for child in sorted(p.glob('**/*'), reverse=True):
                if child.is_dir():
                    child.rmdir()
            p.rmdir()
        except Exception:
            pass

LOCKFILE_NAME = '.graphrag_index.lock'


def _acquire_lock(lock_path: Path) -> tuple[bool, object | None]:
    """Attempt to acquire an exclusive, non-blocking file lock.
    Returns (acquired, handle). Caller must close handle to release.
    """
    try:
        fh = open(lock_path, 'w')
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fh.write(str(os.getpid()))
            fh.flush()
            return True, fh
        except BlockingIOError:
            fh.close()
            return False, None
    except Exception:
        return False, None


def orchestrate(namespace: str, force: bool, dry_run: bool, since: str | None = None, keep: int = 5, gemini_fallback: bool = True) -> dict:
    start = time.time()
    # Use timezone-aware UTC timestamp for directory naming
    ts = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    base_dir = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else Path.cwd()
    artifacts_root = base_dir / 'graphrag_artifacts'
    artifacts_root.mkdir(exist_ok=True)
    staging = artifacts_root / f'run-{ts}'
    status = 'UNKNOWN'
    error = None
    lock_path = artifacts_root / LOCKFILE_NAME
    lock_acquired = False
    lock_handle = None
    # Phase 5 (delta indexing metrics): capture stale vs total docs pre-run
    stale_docs = 0
    total_docs = 0
    stale_doc_ids = []
    try:
        from sqlalchemy import select as _select  # type: ignore
        from app.models.database import IngestLog as _IngestLog
        import asyncio as _asyncio
        async def _load():
            async with db.get_db_session() as session:  # type: ignore
                q = await session.execute(_select(_IngestLog).where(_IngestLog.namespace == namespace))
                rows = q.scalars().all()
                return rows
        if db.async_session is None:  # type: ignore[attr-defined]
            import asyncio as _ai
            _ai.run(db.init_db())  # type: ignore
        rows = _asyncio.run(_load())
        total_docs = len(rows)
        stale_doc_ids = [r.id for r in rows if getattr(r, 'status', '') == 'stale']
        stale_docs = len(stale_doc_ids)
    except Exception:
        pass
    try:
        # Concurrency guard
        lock_acquired, lock_handle = _acquire_lock(lock_path)
        if not lock_acquired and not force:
            return {'status': 'LOCKED', 'duration_s': 0.0, 'staging_dir': None, 'error': 'another index run in progress', 'namespace': namespace, 'dry_run': dry_run, 'stale_docs': stale_docs, 'total_docs': total_docs}

        used_real = False
        gemini_used = False
        run_marker = staging / '_RUNNING'
        success_marker = staging / '_SUCCESS'
        fail_marker = staging / '_FAILED'
        partial_marker = staging / '_PARTIAL'
        if not dry_run:
            # Skip full run if no stale docs and not forced (delta short-circuit)
            if stale_docs == 0 and not force:
                status = 'NOOP'
                graphrag_service.metrics['last_index_run_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                graphrag_service.metrics['last_index_status'] = status
                graphrag_service.metrics['index_runs_total'] = graphrag_service.metrics.get('index_runs_total', 0) + 1
                return {'status': status, 'duration_s': 0.0, 'staging_dir': None, 'error': None, 'namespace': namespace, 'dry_run': dry_run, 'stale_docs': stale_docs, 'total_docs': total_docs}
            staging.mkdir(parents=True, exist_ok=True)
            run_marker.write_text(datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
            try:
                import importlib
                have_openai_key = bool(os.environ.get('OPENAI_API_KEY'))
                if importlib.util.find_spec('graphrag') and have_openai_key:
                    cfg = base_dir / 'graphrag_config.yml'
                    if not cfg.exists():
                        example = base_dir / 'configs' / 'graphrag_config.example.yml'
                        if example.exists():
                            cfg.write_text(example.read_text())
                    console_script = shutil.which('graphrag')
                    if console_script:
                        cmd = [console_script, 'index', '--config', str(cfg), '--output', str(staging)]
                    else:
                        cmd = [sys.executable, '-m', 'graphrag.cli.index', '--config', str(cfg), '--output', str(staging)]
                    if since:
                        cmd += ['--since', since]
                    log_path = staging / 'orchestrator.log'
                    with open(log_path, 'w') as log_fp:
                        proc = subprocess.run(cmd, stdout=log_fp, stderr=log_fp)
                    if proc.returncode != 0:
                        raise RuntimeError(f'graphrag index run failed rc={proc.returncode}; see {log_path}')
                    used_real = True
                elif gemini_fallback:
                    input_dir = base_dir / 'data' / 'raw_docs'
                    # If we have stale_doc_ids, run selective delta index; else full fallback
                    if stale_doc_ids:
                        run_gemini_index(input_dir, staging, stale_doc_ids)
                    else:
                        run_gemini_fallback(input_dir, staging)
                    gemini_used = True
                    used_real = True
            except Exception as e:
                # Attempt fallback only if not yet generated anything
                if gemini_fallback and not used_real:
                    try:
                        input_dir = base_dir / 'data' / 'raw_docs'
                        run_gemini_fallback(input_dir, staging)
                        gemini_used = True
                        used_real = True
                    except Exception:
                        error = str(e)
            if not used_real:
                run_dummy_pipeline(staging)
            status = 'GENERATED'
            # Import using new programmatic API
            try:
                from scripts.import_graphrag_artifacts import import_artifacts
                try:
                    if db.async_session is None:  # type: ignore[attr-defined]
                        import asyncio
                        asyncio.run(db.init_db())
                except Exception:
                    pass
                import_results = import_artifacts(staging, namespace, dry_run=False)
                # Mark only stale docs as indexed now (delta refinement)
                try:
                    from sqlalchemy import update, select  # type: ignore
                    from app.models.database import IngestLog
                    import asyncio
                    async def _mark():
                        async with db.get_db_session() as session:  # type: ignore
                            q = await session.execute(select(IngestLog).where(IngestLog.namespace == namespace, IngestLog.id.in_(stale_doc_ids)))
                            for row in q.scalars().all():
                                row.status = 'indexed'
                                row.last_indexed_at = datetime.now(timezone.utc)
                            await session.commit()
                    if db.async_session is None:
                        asyncio.run(db.init_db())
                    asyncio.run(_mark())
                except Exception:
                    pass
                missing = set(import_results.get('missing', []))
                # Determine partial vs success
                if 'entities' in missing or 'relationships' in missing:
                    status = 'FAILED'
                    fail_marker.write_text('core artifact missing')
                elif missing:
                    status = 'PARTIAL'
                    partial_marker.write_text(json.dumps(list(missing)))
                else:
                    status = 'SUCCESS'
                    success_marker.write_text('ok')
                # Expose import counts in metrics
                try:
                    ent_new = int(import_results.get('entities_new', 0) or 0)
                    ent_merged = int(import_results.get('entities_merged', 0) or 0)
                    rel_new = int(import_results.get('relationships_new', 0) or 0)
                    rel_merged = int(import_results.get('relationships_merged', 0) or 0)
                    graphrag_service.metrics['last_index_entities_new'] = ent_new
                    graphrag_service.metrics['last_index_entities_merged'] = ent_merged
                    graphrag_service.metrics['last_index_relationships_new'] = rel_new
                    graphrag_service.metrics['last_index_relationships_merged'] = rel_merged
                    # Phase 5 reuse metrics
                    graphrag_service.metrics['last_index_delta_nodes'] = ent_new
                    graphrag_service.metrics['last_index_delta_edges'] = rel_new
                    ent_den = ent_new + ent_merged
                    rel_den = rel_new + rel_merged
                    graphrag_service.metrics['last_index_percent_reused_nodes'] = (round(ent_merged / ent_den, 6) if ent_den else None)
                    graphrag_service.metrics['last_index_percent_reused_edges'] = (round(rel_merged / rel_den, 6) if rel_den else None)
                    graphrag_service.metrics['last_index_missing_optional'] = len(missing)
                except Exception:
                    pass
            except Exception as e:  # pragma: no cover
                status = 'IMPORT_FAILED'
                fail_marker.write_text(f'import failed: {e}')
        else:
            status = 'DRY_RUN'
    except Exception as e:  # pragma: no cover
        error = str(e)
        status = 'FAILED'
    dur = round(time.time() - start, 3)
    # Retention prune (best effort)
    try:
        _prune_old_runs(artifacts_root, keep=keep)
    except Exception:
        pass
    # Maintain 'latest' symlink for SUCCESS/PARTIAL runs
    try:
        if status in {'SUCCESS', 'PARTIAL'}:
            link = artifacts_root / 'latest'
            if link.exists() or link.is_symlink():
                try:
                    if link.is_symlink() or link.is_file():
                        link.unlink()
                    elif link.is_dir():
                        shutil.rmtree(link)
                except Exception:
                    pass
            try:
                # Use relative symlink for portability
                rel_target = Path('run-' + ts)
                os.symlink(rel_target, link)
            except Exception:
                pass
    except Exception:
        pass
    # Update metrics (best effort)
    try:
        graphrag_service.metrics['last_index_run_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        graphrag_service.metrics['last_index_duration_s'] = dur
        graphrag_service.metrics['last_index_status'] = status
        graphrag_service.metrics['index_runs_total'] = graphrag_service.metrics.get('index_runs_total', 0) + 1
        # Outcome counters
        key_map = {
            'SUCCESS': 'index_runs_success_total',
            'PARTIAL': 'index_runs_partial_total',
            'FAILED': 'index_runs_failed_total',
            'IMPORT_FAILED': 'index_runs_import_failed_total',
            'DRY_RUN': 'index_runs_dry_total',
            'LOCKED': 'index_runs_locked_total'
        }
        k = key_map.get(status)
        if k:
            graphrag_service.metrics[k] = graphrag_service.metrics.get(k, 0) + 1
        # Delta metrics stored each run
        graphrag_service.metrics['last_index_stale_docs'] = stale_docs
        graphrag_service.metrics['last_index_total_docs'] = total_docs
        try:
            # compute indexed docs after run for convenience
            from sqlalchemy import select as _select2  # type: ignore
            from app.models.database import IngestLog as _IngestLog2
            import asyncio as _asyncio2
            async def _count2():
                async with db.get_db_session() as session:  # type: ignore
                    q = await session.execute(_select2(_IngestLog2).where(_IngestLog2.namespace == namespace, _IngestLog2.status == 'indexed'))
                    return len(q.scalars().all())
            indexed_docs = _asyncio2.run(_count2())
            graphrag_service.metrics['last_index_indexed_docs'] = indexed_docs
            # Also capture current totals for nodes/edges to aid dashboards
            try:
                from sqlalchemy import func as _func2, select as _sel3  # type: ignore
                from app.models.database import GraphNode as _GraphNode2, GraphEdge as _GraphEdge2
                async def _totals():
                    async with db.get_db_session() as session:  # type: ignore
                        n = (await session.execute(_sel3(_func2.count()).select_from(_GraphNode2))).scalar() or 0
                        e = (await session.execute(_sel3(_func2.count()).select_from(_GraphEdge2))).scalar() or 0
                        return int(n), int(e)
                n_total, e_total = _asyncio2.run(_totals())
                graphrag_service.metrics['last_index_nodes_total'] = n_total
                graphrag_service.metrics['last_index_edges_total'] = e_total
            except Exception:
                pass
        except Exception:
            pass
    except Exception:
        pass
    finally:
        if lock_acquired and lock_handle:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                lock_handle.close()
            except Exception:
                pass
            # Remove stale lock file if empty
            try:
                if lock_path.exists() and lock_path.stat().st_size < 32:
                    lock_path.unlink()
            except Exception:
                pass
    return {'status': status, 'duration_s': dur, 'staging_dir': str(staging), 'error': error, 'namespace': namespace, 'dry_run': dry_run, 'stale_docs': stale_docs, 'total_docs': total_docs}


def main():
    ap = argparse.ArgumentParser(description='Run GraphRAG batch index (Phase 2 skeleton).')
    ap.add_argument('--namespace', default='public')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--since', help='Only reindex content updated since timestamp (ISO8601) (placeholder)', default=None)
    ap.add_argument('--keep', type=int, default=5, help='Number of past run-* directories to retain')
    args = ap.parse_args()
    result = orchestrate(args.namespace, args.force, args.dry_run, since=args.since, keep=args.keep, gemini_fallback=True)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] in {'SUCCESS', 'DRY_RUN'} else 1

if __name__ == '__main__':
    raise SystemExit(main())
