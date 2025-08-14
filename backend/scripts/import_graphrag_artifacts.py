#!/usr/bin/env python
"""GraphRAG Artifact Import Utility
=================================

Primary responsibilities (Phase 1):
 - Load GraphRAG output artifacts (entities / relationships / communities / community_reports)
 - Idempotent upsert into local graph tables (merge semantics)
 - Provide summary statistics of new vs merged records

Enhancements (Phase 2):
 - Expose a callable function ``import_artifacts(path, namespace, dry_run=False)`` returning the summary dict
     so the batch orchestrator can directly capture import metrics without scraping stdout.

CLI Usage:
    python -m scripts.import_graphrag_artifacts --path ./graphrag_output --namespace public

Exit Codes:
    0 success (even if some files missing)
    2 path not found / fatal IO
    3 schema validation error

Note: Missing optional files (e.g. community_reports) are logged as warnings but do not fail the run.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy import select
from app.core.database import get_db_session
from app.models.database import (
    GraphNode, GraphEdge, GraphClusterMembership, GraphClusterSummary
)
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='[import-graphrag] %(levelname)s %(message)s')
log = logging.getLogger(__name__)

FILENAMES = {
    'entities': 'entities',
    'relationships': 'relationships',
    'communities': 'communities',
    'community_reports': 'community_reports'
}

EXTS = ('.parquet', '.csv')


def _find_file(base: Path, key: str) -> Optional[Path]:
    for ext in EXTS:
        # prioritize exact match variants
        for cand in base.glob(f'*{FILENAMES[key]}*{ext}'):
            if cand.is_file():
                return cand
    return None


def _load_df(path: Path) -> pd.DataFrame:
    if path.suffix == '.parquet':
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _norm_relation(v: str) -> str:
    v = (v or '').strip()
    if not v:
        return 'RELATED_TO'
    return v.upper()


def upsert_entities(df: pd.DataFrame, namespace: str) -> Tuple[int, int]:
    new_count = merged = 0
    required_cols = {'entity_id', 'name'} & set(df.columns)
    if 'entity_id' not in df.columns:
        # fall back to id or id column
        if 'id' in df.columns:
            df = df.rename(columns={'id': 'entity_id'})
    if 'entity_id' not in df.columns:
        raise ValueError('entities dataframe missing entity_id/id column')
    async def _run():
        nonlocal new_count, merged
        async with get_db_session() as session:
            existing_q = await session.execute(select(GraphNode).where(GraphNode.namespace == namespace))
            existing = existing_q.scalars().all()
            name_index = {(n.name or '').lower(): n for n in existing}
            id_index = {n.id: n for n in existing}
            for rec in df.to_dict(orient='records'):
                eid = str(rec.get('entity_id') or rec.get('id') or uuid.uuid4())
                name = rec.get('name') or eid
                label = rec.get('type') or rec.get('entity_type') or 'Entity'
                emb = rec.get('embedding') if 'embedding' in rec else None
                community_id = rec.get('community_id')
                community_level = rec.get('community_level')
                target = id_index.get(eid) or name_index.get(name.lower())
                if target:
                    # merge
                    props = target.properties or {}
                    if community_id and 'community_id' not in props:
                        props['community_id'] = community_id
                    if community_level and 'community_level' not in props:
                        props['community_level'] = community_level
                    if rec.get('description') and 'summary' not in props:
                        props['summary'] = rec.get('description')
                    props['gr_source'] = 'graphrag_artifact'
                    target.properties = props
                    if (not target.embedding) and emb:
                        try:
                            if isinstance(emb, str):
                                import ast
                                emb_val = ast.literal_eval(emb)
                            else:
                                emb_val = emb
                            target.embedding = emb_val if isinstance(emb_val, list) else []
                        except Exception:
                            pass
                    merged += 1
                else:
                    n = GraphNode(
                        id=eid,
                        label=str(label)[:64],
                        name=str(name)[:256],
                        properties={
                            'community_id': community_id,
                            'community_level': community_level,
                            'summary': rec.get('description') or rec.get('summary'),
                            'gr_source': 'graphrag_artifact',
                            'namespace': namespace,
                        },
                        source_ids=[],
                        embedding=[] if emb is None else (emb if isinstance(emb, list) else []),
                        namespace=namespace,
                    )
                    session.add(n)
                    new_count += 1
            await session.commit()
    import asyncio
    asyncio.run(_run())
    return new_count, merged


def upsert_relationships(df: pd.DataFrame, namespace: str) -> Tuple[int, int]:
    new_count = merged = 0
    if 'relationship_id' not in df.columns:
        if 'id' in df.columns:
            df = df.rename(columns={'id': 'relationship_id'})
    src_col = None
    for c in ['src_id', 'source_id', 'from_id']:
        if c in df.columns: src_col = c; break
    dst_col = None
    for c in ['dst_id', 'target_id', 'to_id']:
        if c in df.columns: dst_col = c; break
    if not src_col or not dst_col:
        raise ValueError('relationships dataframe missing source/target columns')
    async def _run():
        nonlocal new_count, merged
        async with get_db_session() as session:
            existing_q = await session.execute(select(GraphEdge))
            existing = existing_q.scalars().all()
            edge_index = {(e.source_id, e.target_id, e.relation): e for e in existing if (e.properties or {}).get('namespace') == namespace}
            for rec in df.to_dict(orient='records'):
                rid = str(rec.get('relationship_id') or uuid.uuid4())
                s = rec.get(src_col); t = rec.get(dst_col)
                if not s or not t: continue
                rel = _norm_relation(str(rec.get('relationship_type') or rec.get('relation') or 'RELATED_TO'))
                weight = rec.get('weight') or rec.get('relationship_weight')
                conf = rec.get('confidence') or (float(weight) if isinstance(weight,(int,float)) else 0.6)
                key = (s, t, rel)
                existing_edge = edge_index.get(key)
                if existing_edge:
                    props = existing_edge.properties or {}
                    if weight and 'weight' not in props:
                        props['weight'] = weight
                    props['gr_source'] = 'graphrag_artifact'
                    existing_edge.properties = props
                    if conf and (existing_edge.confidence or 0) < conf:
                        existing_edge.confidence = conf
                    merged += 1
                else:
                    e = GraphEdge(
                        id=rid,
                        source_id=s,
                        target_id=t,
                        relation=rel,
                        confidence=conf,
                        properties={'weight': weight, 'namespace': namespace, 'gr_source': 'graphrag_artifact'}
                    )
                    session.add(e)
                    new_count += 1
            await session.commit()
    import asyncio
    asyncio.run(_run())
    return new_count, merged


def upsert_communities(df: pd.DataFrame, namespace: str) -> int:
    added = 0
    if 'community_id' not in df.columns:
        if 'id' in df.columns:
            df = df.rename(columns={'id': 'community_id'})
    async def _run():
        nonlocal added
        async with get_db_session() as session:
            existing_q = await session.execute(select(GraphClusterMembership).where(GraphClusterMembership.namespace == namespace))
            existing = existing_q.scalars().all()
            existing_pairs = {(m.node_id, m.cluster_id) for m in existing}
            for rec in df.to_dict(orient='records'):
                cid = rec.get('community_id');
                nid = rec.get('entity_id') or rec.get('node_id')
                if not cid or not nid: continue
                pair = (nid, cid)
                if pair in existing_pairs: continue
                m = GraphClusterMembership(node_id=nid, cluster_id=cid, namespace=namespace, algorithm='graphrag', score=None)
                session.add(m)
                added += 1
            await session.commit()
    import asyncio
    asyncio.run(_run())
    return added


def upsert_community_reports(df: pd.DataFrame, namespace: str) -> int:
    added = 0
    async def _run():
        nonlocal added
        async with get_db_session() as session:
            existing_q = await session.execute(select(GraphClusterSummary).where(GraphClusterSummary.namespace == namespace))
            existing = existing_q.scalars().all()
            existing_index = {(s.cluster_id, s.algorithm): s for s in existing if s.algorithm == 'graphrag'}
            for rec in df.to_dict(orient='records'):
                cid = rec.get('community_id') or rec.get('cluster_id')
                if not cid: continue
                label = rec.get('report_title') or rec.get('title') or f"Community {cid}"
                summary = rec.get('report_summary') or rec.get('summary')
                key = (cid, 'graphrag')
                existing_s = existing_index.get(key)
                if existing_s:
                    # update only if summary empty
                    if not existing_s.summary and summary:
                        existing_s.summary = summary
                        existing_s.label = label
                else:
                    s = GraphClusterSummary(cluster_id=cid, namespace=namespace, algorithm='graphrag', label=label, summary=summary)
                    session.add(s)
                    added += 1
            await session.commit()
    import asyncio
    asyncio.run(_run())
    return added


def import_artifacts(path: str | Path, namespace: str = 'public', dry_run: bool = False) -> Dict[str, Any]:
    """Programmatic import entrypoint used by orchestrator.

    Returns a summary dict; missing files are recorded under 'missing'.
    """
    base = Path(path)
    results: Dict[str, Any] = {"namespace": namespace, "dry_run": dry_run, "missing": []}
    if not base.exists():
        raise FileNotFoundError(f"Artifact path does not exist: {base}")

    # Entities
    f_entities = _find_file(base, 'entities')
    if f_entities:
        df_ent = _load_df(f_entities)
        if not dry_run:
            new_c, merged_c = upsert_entities(df_ent, namespace)
            results['entities_new'] = new_c; results['entities_merged'] = merged_c
        else:
            results['entities_rows'] = len(df_ent)
    else:
        log.warning('Entities file not found')
        results['missing'].append('entities')
    # Relationships
    f_rel = _find_file(base, 'relationships')
    if f_rel:
        df_rel = _load_df(f_rel)
        if not dry_run:
            new_e, merged_e = upsert_relationships(df_rel, namespace)
            results['relationships_new'] = new_e; results['relationships_merged'] = merged_e
        else:
            results['relationships_rows'] = len(df_rel)
    else:
        log.warning('Relationships file not found')
        results['missing'].append('relationships')
    # Communities
    f_comm = _find_file(base, 'communities')
    if f_comm:
        df_comm = _load_df(f_comm)
        if not dry_run:
            added = upsert_communities(df_comm, namespace)
            results['community_memberships_added'] = added
        else:
            results['communities_rows'] = len(df_comm)
    else:
        log.warning('Communities file not found')
        results['missing'].append('communities')
    # Reports
    f_reports = _find_file(base, 'community_reports')
    if f_reports:
        df_rep = _load_df(f_reports)
        if not dry_run:
            added = upsert_community_reports(df_rep, namespace)
            results['community_reports_added'] = added
        else:
            results['community_reports_rows'] = len(df_rep)
    else:
        log.warning('Community reports file not found')
        results['missing'].append('community_reports')
    return results


def main():
    p = argparse.ArgumentParser(description='Import GraphRAG artifacts into local graph store.')
    p.add_argument('--path', required=True, help='Directory containing GraphRAG artifact files')
    p.add_argument('--namespace', default='public')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    base = Path(args.path)
    if not base.exists():
        log.error('Path does not exist: %s', base)
        return 2
    try:
        results = import_artifacts(base, args.namespace, dry_run=args.dry_run)
    except Exception as e:  # pragma: no cover
        log.error('Import failed: %s', e)
        return 3
    print(json.dumps(results, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
