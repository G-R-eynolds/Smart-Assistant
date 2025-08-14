import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import networkx as nx

from app.core.database import get_db_session
from app.models.database import (
    GraphNode,
    GraphEdge,
    GraphClusterMembership,
    GraphClusterSummary,
)
from app.core.config import settings
from app.core.gemini_client import gemini_client

logger = logging.getLogger(__name__)

@dataclass
class ClusterResult:
    clusters: List[Dict]
    stats: Dict[str, float]
    generated_at: float
    algorithm: str = "louvain"
    modularity: Optional[float] = None

class ClusterService:
    """Phase 3 cluster computation (Louvain via networkx + LLM summaries).

    Strategy:
      1. Build networkx graph for given namespace
      2. Run community detection (greedy modularity communities as proxy for Louvain)
         - networkx has community.louvain_communities in newer versions; fallback to greedy if absent
      3. Persist memberships (wipe prior algorithm rows for namespace)
      4. Compute per-cluster top terms from node names + chunk text tokens (light heuristic)
      5. Summaries on-demand (POST summarize) with caching table
    Caching: in-memory TTL + DB persistence for membership.
    """
    def __init__(self) -> None:
        # In-memory caches & thresholds
        self._cache: Dict[Tuple[str, str], ClusterResult] = {}
        self._ttl = 600.0  # seconds for cluster result cache
        self._last_counts: Dict[Tuple[str, str], int] = {}
        self._recompute_inflight: Dict[Tuple[str, str], bool] = {}
        self._min_growth_absolute = 50  # trigger recompute if >= 50 new nodes
        self._min_growth_ratio = 0.1    # or growth >=10%
        # Summarization budgeting and rate limiting
        self._summary_tokens_used: Dict[str, int] = {}
        self._summary_calls_window: Dict[str, List[float]] = {}

    async def compute_if_stale(self, namespace: Optional[str] = None, force: bool = False) -> ClusterResult:
        ns = namespace or settings.DEFAULT_NAMESPACE
        key = (ns, "louvain")
        now = time.time()
        if not force:
            cached = self._cache.get(key)
            if cached and now - cached.generated_at < self._ttl:
                return cached
        async with get_db_session() as session:
            assert isinstance(session, AsyncSession)
            node_q = await session.execute(select(GraphNode).where((GraphNode.namespace == ns) | (GraphNode.namespace.is_(None))))
            nodes = [n for n in node_q.scalars().all() if (n.namespace or settings.DEFAULT_NAMESPACE) == ns]
            edge_q = await session.execute(select(GraphEdge))
            edges = [e for e in edge_q.scalars().all() if (e.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns]
            # Ensure simple deterministic layout positions for nodes missing one (radial by sorted name)
            try:
                missing = [n for n in nodes if not ((n.properties or {}).get("layout"))]
                if missing:
                    total = len(nodes)
                    for idx, n in enumerate(sorted(nodes, key=lambda z: (z.name or z.id))):
                        props = n.properties or {}
                        if not props.get("layout"):
                            angle = 2.0 * 3.1415926535 * (idx / max(1, total))
                            props["layout"] = {"x": float(f"{(0.85 * __import__('math').cos(angle)):.4f}"), "y": float(f"{(0.85 * __import__('math').sin(angle)):.4f}")}
                            n.properties = props
                    await session.commit()
            except Exception as e:
                logger.warning(f"[ClusterService] layout assignment failed: {e}")
            # Build undirected weighted graph for communities
            G = nx.Graph()
            for n in nodes:
                G.add_node(n.id, label=n.label, name=n.name)
            for e in edges:
                # treat as undirected for community detection
                if G.has_node(e.source_id) and G.has_node(e.target_id):
                    G.add_edge(e.source_id, e.target_id, weight=e.confidence or 1.0)
            if G.number_of_nodes() == 0:
                result = ClusterResult(clusters=[], stats={"clusters":0, "nodes":0}, generated_at=now)
                self._cache[key] = result
                return result
            try:
                # networkx >=3.2 provides community.louvain_communities
                from networkx.algorithms.community import louvain_communities, modularity
                communities = list(louvain_communities(G, weight="weight", seed=42))  # type: ignore
                try:
                    mod = modularity(G, communities, weight="weight")
                except Exception:
                    mod = None
            except Exception:
                from networkx.algorithms.community import greedy_modularity_communities, modularity
                communities = list(greedy_modularity_communities(G, weight="weight"))  # type: ignore
                try:
                    mod = modularity(G, communities, weight="weight")
                except Exception:
                    mod = None
            # Persist memberships: clear old
            await session.execute(delete(GraphClusterMembership).where(
                GraphClusterMembership.namespace == ns,
                GraphClusterMembership.algorithm == "louvain",
            ))
            cluster_payload: List[Dict] = []
            for idx, comm in enumerate(sorted(communities, key=lambda c: -len(c))):
                cid = f"c{idx+1}"
                for node_id in comm:
                    session.add(GraphClusterMembership(node_id=node_id, cluster_id=cid, namespace=ns, algorithm="louvain"))
                # sample nodes for preview
                sample_nodes = []
                for nid in list(comm)[:12]:
                    node_obj = next((n for n in nodes if n.id == nid), None)
                    if node_obj and node_obj.name:
                        sample_nodes.append(node_obj.name)
                # centroid calculation using stored layout positions if present
                xs = []
                ys = []
                for nid in comm:
                    node_obj = next((n for n in nodes if n.id == nid), None)
                    if not node_obj:
                        continue
                    lay = (node_obj.properties or {}).get("layout") or {}
                    x = lay.get("x")
                    y = lay.get("y")
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        xs.append(x)
                        ys.append(y)
                centroid = {"x": sum(xs)/len(xs) if xs else 0.0, "y": sum(ys)/len(ys) if ys else 0.0}
                cluster_payload.append({
                    "id": cid,
                    "size": len(comm),
                    "node_ids": list(comm),
                    "sample_nodes": sample_nodes[:8],
                    "centroid": centroid,
                })
            await session.commit()
        result = ClusterResult(
            clusters=cluster_payload,
            stats={"clusters": len(cluster_payload), "nodes": len(nodes)},
            generated_at=now,
            algorithm="louvain",
            modularity=mod,
        )
        self._cache[key] = result
        return result

    async def get_clusters(self, namespace: Optional[str] = None, force: bool = False) -> ClusterResult:
        return await self.compute_if_stale(namespace=namespace, force=force)

    async def _maybe_recompute(self, namespace: str):
        key = (namespace, "louvain")
        if self._recompute_inflight.get(key):
            return
        self._recompute_inflight[key] = True
        try:
            # Get current node count
            async with get_db_session() as session:
                from sqlalchemy import select, func
                res = await session.execute(select(func.count()).select_from(GraphNode).where((GraphNode.namespace == namespace) | (GraphNode.namespace.is_(None))))
                count = int(res.scalar() or 0)
            prev = self._last_counts.get(key)
            if prev is None or count - prev >= self._min_growth_absolute or (prev and (count - prev)/max(prev,1) >= self._min_growth_ratio):
                logger.info(f"[ClusterService] Triggering background recompute for namespace={namespace} count={count} prev={prev}")
                await self.compute_if_stale(namespace=namespace, force=True)
                self._last_counts[key] = count
        except Exception as e:
            logger.warning(f"[ClusterService] Background recompute failed: {e}")
        finally:
            self._recompute_inflight[key] = False

    def trigger_background_recompute(self, namespace: Optional[str]):
        """Fire-and-forget background recompute if growth thresholds exceeded."""
        import asyncio
        ns = namespace or settings.DEFAULT_NAMESPACE
        asyncio.create_task(self._maybe_recompute(ns))

    async def summarize_clusters(self, namespace: Optional[str], cluster_ids: List[str], max_tokens: int = 120) -> Dict[str, Dict[str,str]]:
        """Summarize clusters using Gemini; cached by top_terms hash (simplified: node name tokens).
        Returns mapping cluster_id -> {label, summary}.
        """
        ns = namespace or settings.DEFAULT_NAMESPACE
        # Compute ensuring membership exists
        await self.get_clusters(namespace=ns)
        summaries: Dict[str, Dict[str,str]] = {}
        async with get_db_session() as session:
            assert isinstance(session, AsyncSession)
            for cid in cluster_ids:
                # Rate limiting (simple sliding window per namespace)
                now = time.time()
                window_key = f"{ns}:window"
                calls = self._summary_calls_window.setdefault(window_key, [])
                calls[:] = [t for t in calls if now - t < 60]
                if len(calls) >= settings.CLUSTER_SUMMARY_RATE_LIMIT_PER_MIN:
                    logger.warning("Cluster summarize rate limit hit for namespace=%s", ns)
                    summaries[cid] = {"label": f"{cid}", "summary": "Rate limit exceeded; try later."}
                    continue
                calls.append(now)
                # Token budget check
                used = self._summary_tokens_used.get(ns, 0)
                if used >= settings.CLUSTER_SUMMARY_DAILY_TOKEN_BUDGET:
                    summaries[cid] = {"label": cid, "summary": "Budget exhausted; skipping summary."}
                    continue
                # Fetch membership nodes
                mem_q = await session.execute(select(GraphClusterMembership.node_id).where(
                    GraphClusterMembership.namespace == ns,
                    GraphClusterMembership.cluster_id == cid,
                    GraphClusterMembership.algorithm == "louvain"
                ))
                node_ids = [r[0] for r in mem_q.all()]
                if not node_ids:
                    continue
                n_q = await session.execute(select(GraphNode).where(GraphNode.id.in_(node_ids)))
                members = n_q.scalars().all()
                # Derive simple top terms by frequency of lowercased words in names
                from collections import Counter
                words: List[str] = []
                for n in members:
                    if n.name:
                        for w in n.name.split():
                            w2 = ''.join(ch for ch in w.lower() if ch.isalnum())
                            if 2 <= len(w2) <= 30:
                                words.append(w2)
                ctr = Counter(words)
                top_terms = [w for w,_ in ctr.most_common(8)]
                top_terms_hash = '|'.join(top_terms)
                # Check cache table
                existing_q = await session.execute(select(GraphClusterSummary).where(
                    GraphClusterSummary.namespace == ns,
                    GraphClusterSummary.cluster_id == cid,
                    GraphClusterSummary.algorithm == "louvain",
                    GraphClusterSummary.top_terms_hash == top_terms_hash
                ))
                existing = existing_q.scalars().first()
                if existing:
                    summaries[cid] = {"label": existing.label or "", "summary": existing.summary or ""}
                    continue
                if not gemini_client.is_configured():
                    # Fallback label only
                    label = ' '.join(top_terms[:3]) or f"Cluster {cid}"
                    summary_text = "LLM disabled; heuristic label derived from frequent terms." 
                else:
                    prompt = (
                        "You are labeling graph clusters. Given TOP_TERMS: " + ', '.join(top_terms) +
                        " SAMPLE_ENTITIES: " + ', '.join([m.name for m in members if m.name][:6]) +
                        " Return JSON with keys label (<12 words) and summary (2 concise sentences)."
                    )
                    try:
                        allowed_tokens = min(max_tokens, settings.CLUSTER_SUMMARY_MAX_TOKENS_PER)
                        if used + allowed_tokens > settings.CLUSTER_SUMMARY_DAILY_TOKEN_BUDGET:
                            allowed_tokens = max(0, settings.CLUSTER_SUMMARY_DAILY_TOKEN_BUDGET - used)
                        resp = await gemini_client.summarize_cluster(prompt, max_tokens=allowed_tokens)
                        label = resp.get('label') or resp.get('title') or 'Cluster'
                        summary_text = resp.get('summary') or resp.get('text') or ''
                        self._summary_tokens_used[ns] = used + allowed_tokens
                    except Exception as e:
                        logger.warning(f"Cluster summarize failed {cid}: {e}")
                        label = ' '.join(top_terms[:3]) or f"Cluster {cid}"
                        summary_text = "Heuristic fallback summary."
                # Persist summary
                rec = GraphClusterSummary(
                    cluster_id=cid,
                    namespace=ns,
                    algorithm="louvain",
                    top_terms_hash=top_terms_hash,
                    label=label[:120],
                    summary=summary_text[:800],
                )
                session.add(rec)
                await session.commit()
                summaries[cid] = {"label": label, "summary": summary_text}
        return summaries

cluster_service = ClusterService()
