"""GraphRAG Query Adapter (Phase 3)

Provides a unified interface for enhanced query modes:
  - global: broad graph-wide semantic + structural search
  - local: neighborhood-expansion search anchored on entity matches
  - drift: fallback reasoning path when query appears out-of-domain
  - auto: heuristic selection among above modes

If official GraphRAG query pipeline is unavailable (e.g. missing OPENAI key or library),
falls back to existing graphrag_service.hybrid_retrieve for all modes with light weighting.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import math
import time
import os
from pathlib import Path
from app.core.config import settings

from app.core.graphrag_service import graphrag_service
try:
    from sqlalchemy import select as _sa_select  # type: ignore
except Exception:  # pragma: no cover - environment without sqlalchemy
    _sa_select = None  # type: ignore
from app.core.database import get_db_session
from app.models.database import GraphEdge

class QueryAdapter:
    def __init__(self):
        self.enabled = graphrag_service.enabled
        # Detect availability of official GraphRAG library query components
        try:
            import importlib
            self._gr_lib_available = importlib.util.find_spec('graphrag') is not None
        except Exception:
            self._gr_lib_available = False
        # Artifact cache (entities / relationships) for structured search path
        self._artifact_cache: dict[str, Any] = {
            'version': None,
            'entities': None,
            'relationships': None,
        }
        self._entity_embed_cache = {}

    def _artifact_version(self, latest: Path) -> str:
        try:
            ents = next(iter(latest.glob('*entities*.*')), None)
            rels = next(iter(latest.glob('*relationships*.*')), None)
            stat_bits = []
            for f in [ents, rels]:
                if f and f.exists():
                    st = f.stat()
                    stat_bits.append(f.name + str(int(st.st_mtime)))
            return '|'.join(stat_bits)
        except Exception:
            return 'missing'

    def _load_artifacts_cached(self, base_dir: Path) -> tuple[list[dict], list[dict]]:
        """Load entities & relationships artifacts with in-memory caching.

        Cache invalidates when underlying files (entities/relationships) mtime changes
        or latest symlink target changes.
        """
        artifacts_root = base_dir / 'graphrag_artifacts'
        latest = artifacts_root / 'latest'
        if not latest.exists():
            runs = sorted([p for p in artifacts_root.glob('run-*') if p.is_dir()], reverse=True)
            if not runs:
                return [], []
            latest = runs[0]
        version = self._artifact_version(latest)
        if self._artifact_cache['version'] == version and self._artifact_cache['entities'] is not None:
            try:
                graphrag_service.metrics['artifact_cache_hits'] = graphrag_service.metrics.get('artifact_cache_hits', 0) + 1
            except Exception:
                pass
            return self._artifact_cache['entities'], self._artifact_cache['relationships']
        try:
            graphrag_service.metrics['artifact_cache_misses'] = graphrag_service.metrics.get('artifact_cache_misses', 0) + 1
        except Exception:
            pass
        ents_file = next(iter(latest.glob('*entities*.*')), None)
        rel_file = next(iter(latest.glob('*relationships*.*')), None)
        if not ents_file or not rel_file:
            return [], []
        ents_df = None
        rels_df = None
        try:
            import pandas as _pd  # type: ignore
            try:
                ents_df = _pd.read_csv(ents_file) if ents_file.suffix == '.csv' else _pd.read_parquet(ents_file)
            except Exception:
                return [], []
            try:
                rels_df = _pd.read_csv(rel_file) if rel_file.suffix == '.csv' else _pd.read_parquet(rel_file)
            except Exception:
                rels_df = None
        except Exception:
            # pandas not available; abort cache load
            return [], []
        entities: list[dict] = []
        rels: list[dict] = []
        if ents_df is not None:
            for rec in ents_df.to_dict(orient='records')[:5000]:
                eid = str(rec.get('entity_id') or rec.get('id'))
                if not eid:
                    continue
                entities.append(rec)
        if rels_df is not None:
            for rec in rels_df.to_dict(orient='records')[:15000]:
                rels.append(rec)
        self._artifact_cache = {
            'version': version,
            'entities': entities,
            'relationships': rels,
        }
        try:
            graphrag_service.metrics['artifact_cache_reload_count'] = graphrag_service.metrics.get('artifact_cache_reload_count', 0) + 1
        except Exception:
            pass
        return entities, rels

    async def query(
        self,
        query: str,
        mode: str = "auto",
        top_k: int = 8,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        if not self.enabled:
            return {"success": False, "error": "GraphRAG disabled"}
        decided_mode = mode
        # Auto mode heuristic: if query length < 5 tokens -> global; else local first
        if mode == "auto":
            toks = query.split()
            decided_mode = "global" if len(toks) <= 4 else "local"

        # Attempt real GraphRAG query pipeline if library + OpenAI key present
        base = None
        if (not settings.GRAPHRAG_FORCE_GEMINI_STRUCTURED) and self._gr_lib_available and os.environ.get('OPENAI_API_KEY'):
            try:
                base = await self._run_real_graphrag_query(query, decided_mode, top_k, namespace)
            except Exception:
                base = None

        if base is None:
            # Try Gemini-native structured search over artifacts
            gem_base = await self._run_gemini_structured_query(query, decided_mode, top_k)
            base = gem_base or await graphrag_service.hybrid_retrieve(query=query, top_k=top_k * 3, namespace=namespace)

        base_nodes = base.get("nodes", []) if isinstance(base, dict) else base
        cand_ids = [n.get("id") for n in base_nodes if isinstance(n, dict) and n.get("id")]

        # Fetch edges among candidates for relation weighting
        edge_counts: dict[str, float] = {}
        rel_weight: dict[str, float] = {
            "RELATED_TO": 0.6,
            "CO_OCCURS": 0.75,
            "MENTIONED_IN": 0.4,
            "ROLE_AT": 0.9,
            "USES_TECH": 0.85,
            "HAS_ENTITY": 0.5,
            "CONTAINS": 0.45,
        }
        if cand_ids and _sa_select is not None:
            async with get_db_session() as session:  # type: ignore
                eq = await session.execute(
                    _sa_select(GraphEdge).where((GraphEdge.source_id.in_(cand_ids)) | (GraphEdge.target_id.in_(cand_ids)))
                )
                for e in eq.scalars().all():
                    if e.source_id in cand_ids:
                        edge_counts[e.source_id] = edge_counts.get(e.source_id, 0.0) + rel_weight.get(e.relation, 0.6)
                    if e.target_id in cand_ids:
                        edge_counts[e.target_id] = edge_counts.get(e.target_id, 0.0) + rel_weight.get(e.relation, 0.6)

        # Score candidates
        scored = []
        q_terms = {t.lower() for t in query.split() if t}
        for r in base_nodes:
            if not isinstance(r, dict):
                continue
            props = r.get("properties") or {}
            deg_norm = float(props.get("degree_norm") or 0.0)
            rel_sum = edge_counts.get(r.get("id"), 0.0)
            name = (r.get("name") or "").lower()
            overlap = 0.0
            if name:
                name_terms = {t for t in name.split() if t}
                if name_terms:
                    overlap = len(q_terms & name_terms) / len(q_terms or {1})
            length_penalty = 0.05 if len(name) > 80 else 0.0

            if decided_mode == "global":
                w_c, w_r, w_o = 0.45, 0.35, 0.20
            elif decided_mode == "local":
                w_c, w_r, w_o = 0.35, 0.45, 0.20
            elif decided_mode == "drift":
                w_c, w_r, w_o = 0.25, 0.25, 0.50
            else:
                w_c, w_r, w_o = 0.4, 0.4, 0.2

            raw_score = w_c * deg_norm + w_r * (math.log1p(rel_sum) / 4.0) + w_o * overlap - length_penalty
            scored.append({
                **r,
                "score_breakdown": {"deg_norm": deg_norm, "rel": rel_sum, "overlap": overlap},
                "aug_score": round(raw_score, 6),
            })

        scored.sort(key=lambda x: x["aug_score"], reverse=True)
        out = scored[:top_k]
        dur = round(time.time() - start, 4)

        # Metrics
        try:
            ms = graphrag_service.metrics
            ms["query2_latency_sum"] = ms.get("query2_latency_sum", 0.0) + dur
            ms["query2_latency_count"] = ms.get("query2_latency_count", 0) + 1
            key = f"query2_mode_{decided_mode}_count"
            ms[key] = ms.get(key, 0) + 1
        except Exception:
            pass

        # Reasoning chain
        if decided_mode == "global":
            rc_w_c, rc_w_r, rc_w_o = 0.45, 0.35, 0.20
        elif decided_mode == "local":
            rc_w_c, rc_w_r, rc_w_o = 0.35, 0.45, 0.20
        elif decided_mode == "drift":
            rc_w_c, rc_w_r, rc_w_o = 0.25, 0.25, 0.50
        else:
            rc_w_c, rc_w_r, rc_w_o = 0.4, 0.4, 0.2

        reasoning_chain = [
            {"step": "mode_selection", "mode": decided_mode, "criteria": "len(query) heuristic"},
            {"step": "candidate_scoring", "weights": {"deg_norm": rc_w_c, "relation_sum": rc_w_r, "term_overlap": rc_w_o}},
        ]

        return {
            "success": True,
            "mode_used": decided_mode,
            "results": out,
            "duration_s": dur,
            "total_considered": len(base_nodes),
            "reasoning_chain": reasoning_chain,
        }

    async def _run_real_graphrag_query(self, query: str, mode: str, top_k: int, namespace: Optional[str]):  # pragma: no cover - integration path
        """Invoke GraphRAG library's query pipeline.

        This implementation loads the configured project index (artifacts) and executes
        the query with mode approximations:
          - global -> global semantic search (graph-wide)
          - local -> neighborhood-biased search
          - drift -> falls back to global but flags result

        Requires that graphrag indexing artifacts exist and that OPENAI_API_KEY is set.
        """
        import os
        from graphrag.query.structured_search import basic_search, global_search, local_search, drift_search  # type: ignore
        # Locate latest artifacts directory
        base_dir = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
        artifacts_root = base_dir / 'graphrag_artifacts'
        latest = artifacts_root / 'latest'
        if not latest.exists():
            runs = sorted([p for p in artifacts_root.glob('run-*') if p.is_dir()], reverse=True)
            if not runs:
                return None
            latest = runs[0]
        # Load artifacts via cache
        ents_records, rel_records = self._load_artifacts_cached(base_dir)
        if not ents_records or not rel_records:
            return None
        nodes = []
        node_id_set = set()
        for rec in ents_records:
            eid = str(rec.get('entity_id') or rec.get('id'))
            if not eid or eid in node_id_set:
                continue
            node_id_set.add(eid)
            nodes.append({'id': eid, 'name': rec.get('name'), 'type': rec.get('type', 'Entity'), 'description': rec.get('description')})
        edges = []
        for rec in rel_records:
            s = rec.get('src_id') or rec.get('source_id') or rec.get('from_id')
            t = rec.get('dst_id') or rec.get('target_id') or rec.get('to_id')
            if not s or not t:
                continue
            rel = rec.get('relationship_type') or rec.get('relation') or 'RELATED_TO'
            edges.append({'source_id': s, 'target_id': t, 'type': rel})
        q_terms = {t.lower() for t in query.split() if t}
        degree = {}
        for e in edges:
            degree[e['source_id']] = degree.get(e['source_id'], 0) + 1
            degree[e['target_id']] = degree.get(e['target_id'], 0) + 1
        def relevance(n):
            name = (n.get('name') or '').lower()
            overlap = sum(1 for t in q_terms if t in name)
            return overlap, degree.get(n['id'], 0)
        cand_nodes = sorted(nodes, key=lambda n: relevance(n), reverse=True)[: max(20, top_k*3)]
        search_mode = mode
        if search_mode == 'auto':
            search_mode = 'local'
        try:
            if search_mode == 'global':
                gr_res = global_search.search(query)  # type: ignore
            elif search_mode == 'local':
                gr_res = local_search.search(query)  # type: ignore
            elif search_mode == 'drift':
                gr_res = drift_search.search(query)  # type: ignore
            else:
                gr_res = basic_search.search(query)
        except Exception:
            return None
        out_nodes = []
        try:
            items = gr_res if isinstance(gr_res, list) else [gr_res]
            for item in items:
                ctx = getattr(item, 'context', []) or []
                for c in ctx[: top_k * 3]:
                    nid = getattr(c, 'id', None) or getattr(c, 'entity_id', None) or None
                    name = getattr(c, 'name', None) or getattr(c, 'text', '')[:80]
                    if not name:
                        continue
                    out_nodes.append({'id': nid or name[:60], 'label': 'Entity', 'name': name, 'properties': {'source': 'graphrag_query', 'score': getattr(c, 'score', None)}})
        except Exception:
            return None
        if not out_nodes:
            return None
        return {'nodes': out_nodes[: top_k * 3], 'edges': []}

    async def _run_gemini_structured_query(self, query: str, mode: str, top_k: int):
        """Gemini-native structured search over imported artifacts.

        Combines term overlap, light degree centrality from relationships,
        and optional embedding similarity (Gemini) for entity names.
        """
        base_dir = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
        ents_records, rel_records = self._load_artifacts_cached(base_dir)
        if not ents_records:
            return None
        # Build degree map from relationships
        degree: dict[str, int] = {}
        for rec in rel_records[: 30000]:
            s = rec.get('src_id') or rec.get('source_id') or rec.get('from_id')
            t = rec.get('dst_id') or rec.get('target_id') or rec.get('to_id')
            if not s or not t:
                continue
            degree[s] = degree.get(s, 0) + 1
            degree[t] = degree.get(t, 0) + 1
        # Prefilter by simple term overlap on names
        q_terms = {t.lower() for t in query.split() if t}
        def overlap_score(name: str) -> float:
            if not name:
                return 0.0
            nt = {t for t in name.lower().split() if t}
            return len(q_terms & nt) / max(1, len(q_terms))
        pre = []
        for rec in ents_records:
            eid = str(rec.get('entity_id') or rec.get('id'))
            if not eid:
                continue
            name = rec.get('name') or ''
            pre.append((eid, name, overlap_score(name)))
        pre.sort(key=lambda x: x[2], reverse=True)
        cand = pre[: max(256, top_k*10)]
        # Optional embedding similarity via Gemini
        embed_sim = {}
        try:
            if hasattr(graphrag_service, '_embed_texts') and graphrag_service.embedding_model:
                qv = (await graphrag_service._embed_texts([query]))[0]
                # Gather entity name embeddings
                names = [c[1] for c in cand]
                vecs = []
                # Cache lookups & batched embedding for misses
                missing_idx = []
                for idx, (eid, name, _) in enumerate(cand):
                    if eid in self._entity_embed_cache:
                        vecs.append(self._entity_embed_cache[eid])
                    else:
                        vecs.append(None)
                        missing_idx.append(idx)
                if missing_idx:
                    texts = [cand[i][1] for i in missing_idx]
                    new_vecs = await graphrag_service._embed_texts(texts)
                    for j, i in enumerate(missing_idx):
                        self._entity_embed_cache[cand[i][0]] = new_vecs[j]
                        vecs[i] = new_vecs[j]
                # Compute cosine similarity
                def cos(a, b):
                    if not a or not b:
                        return 0.0
                    import math
                    da = math.sqrt(sum(x*x for x in a)) or 1.0
                    db = math.sqrt(sum(x*x for x in b)) or 1.0
                    s = sum((x*y) for x,y in zip(a,b))
                    return s/(da*db)
                for (eid, name, ov), v in zip(cand, vecs):
                    embed_sim[eid] = cos(qv, v)
        except Exception:
            embed_sim = {}
        # Score candidates
        results = []
        for eid, name, ov in cand:
            deg = degree.get(eid, 0)
            sim = embed_sim.get(eid, 0.0)
            # Weight by mode
            if mode == 'global':
                w_o, w_d, w_s = 0.4, 0.3, 0.3
            elif mode == 'local':
                w_o, w_d, w_s = 0.3, 0.4, 0.3
            else:
                w_o, w_d, w_s = 0.33, 0.34, 0.33
            import math
            score = w_o*ov + w_d*(math.log1p(deg)/4.0) + w_s*sim
            results.append({'id': eid, 'label': 'Entity', 'name': name, 'properties': {'source': 'artifacts', 'deg': deg, 'sim': round(sim,4)} , 'aug_score': round(score,6)})
        results.sort(key=lambda x: x['aug_score'], reverse=True)
        return {'nodes': results[: top_k*3], 'edges': []}


query_adapter = QueryAdapter()
