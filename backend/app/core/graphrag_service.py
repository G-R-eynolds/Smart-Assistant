"""Clean reconstructed GraphRAG service implementation.

Features restored:
- Ingestion (heuristic or LLM extraction) with namespace tagging
- Chunk creation & mention linking
- Optional embeddings (Gemini) with caching
- SQLite storage (GraphNode / GraphEdge) and optional Neo4j upsert
- Hybrid retrieval (embedding cosine -> name contains -> TF term score)
- Answer synthesis (Gemini) using retrieved chunk context
- Shortest path (Neo4j shortestPath or BFS fallback)
- Metrics (counts + latency sums + namespace doc counts)
- Optional Qdrant client initialization (future retrieval extension)

Advanced add-ons (BM25-lite ranking, Qdrant retrieval, richer metrics) will be layered after tests pass.
"""
from __future__ import annotations

import logging
import math
import re
import time
import uuid
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.models.database import GraphNode, GraphEdge
from app.core.gemini_client import gemini_client

try:  # Optional Neo4j
    from neo4j import AsyncGraphDatabase  # type: ignore
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    reasoning: str = ""


class GraphRAGService:
    def __init__(self) -> None:
        self.enabled = settings.ENABLE_GRAPHRAG
        self.graph_store = settings.GRAPH_STORE
        self.embedding_model = settings.EMBEDDING_MODEL or "text-embedding-004"
        self.embedding_cache: Dict[str, List[float]] = {}

        # Optional Neo4j driver
        self.neo4j_driver = None
        if self.graph_store == "neo4j" and AsyncGraphDatabase and settings.NEO4J_URI:
            try:
                auth = None
                if settings.NEO4J_USER and settings.NEO4J_PASSWORD:
                    auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                self.neo4j_driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=auth)
            except Exception:
                logger.exception("neo4j_init_failed – using sqlite fallback")

        # Metrics registry
        self.metrics: Dict[str, Any] = {
            "ingest_count": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "retrieval_requests": 0,
            "answer_requests": 0,
            "ingest_latency_sum": 0.0,
            "ingest_latency_count": 0,
            "retrieval_latency_sum": 0.0,
            "retrieval_latency_count": 0,
            "answer_latency_sum": 0.0,
            "answer_latency_count": 0,
            "namespace_docs": {},
            "snapshots_created": 0,
            "stream_subscribers": 0,
            # Phase 2 index orchestration metrics
            "last_index_run_at": None,
            "last_index_duration_s": None,
            "last_index_status": None,
            "index_runs_total": 0,
        }

        # Optional Qdrant client (future retrieval extension)
        self.qdrant = None
        if getattr(settings, "QDRANT_URL", ""):
            try:
                from qdrant_client import QdrantClient  # type: ignore
                self.qdrant = QdrantClient(url=settings.QDRANT_URL)
            except Exception:
                logger.warning("qdrant_init_failed – skipping external vector store")
        self._qdrant_collection = "graphrag_nodes"
        # Phase 2/5: simple in-process scheduler toggle
        self._scheduler_started = False

    def ensure_scheduler(self, interval_seconds: int = 0):
        """Start lightweight periodic index scheduler if interval > 0 and not already running.
        Uses asyncio.create_task; suitable only for single-process dev environment.
        """
        if self._scheduler_started or interval_seconds <= 0:
            return
        try:
            import asyncio
            async def _loop():
                while True:
                    await asyncio.sleep(interval_seconds)
                    try:
                        from scripts.run_graphrag_index import orchestrate
                        orchestrate(settings.DEFAULT_NAMESPACE, force=False, dry_run=False)
                    except Exception:
                        logger.debug("scheduled_index_run_failed", exc_info=True)
            asyncio.get_event_loop().create_task(_loop())
            self._scheduler_started = True
        except Exception:
            logger.debug("scheduler_init_failed", exc_info=True)

    def _stable_int_id(self, s: str) -> int:
        h = hashlib.sha256(s.encode()).hexdigest()[:16]
        return int(h, 16)

    def _ensure_qdrant_collection(self, dim: int) -> None:
        if not self.qdrant:
            return
        try:  # lazy import of models
            from qdrant_client.http import models as qmodels  # type: ignore
            existing = self.qdrant.get_collections().collections  # type: ignore
            names = {c.name for c in existing}
            if self._qdrant_collection not in names:
                self.qdrant.create_collection(  # type: ignore
                    collection_name=self._qdrant_collection,
                    vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
                )
        except Exception:
            logger.warning("qdrant_collection_ensure_failed")

    # ---------------------- Extraction ----------------------
    async def extract_entities_and_relations(self, text: str) -> ExtractionResult:
        if not gemini_client.is_configured():  # type: ignore[attr-defined]
            return self._heuristic_extract(text)
        try:
            data = await gemini_client.extract_entities_relations(text)  # type: ignore
            nodes = data.get("entities") or data.get("nodes") or []
            rels = data.get("relations") or data.get("edges") or []
            node_objs: List[Dict[str, Any]] = []
            for e in nodes[:200]:
                name = e.get("name")
                if not name:
                    continue
                node_objs.append(
                    {
                        "id": str(uuid.uuid4()),
                        "label": e.get("type", "Entity"),
                        "name": name,
                        "properties": {"description": e.get("description", ""), "source": "gemini"},
                    }
                )
            by_name = {n["name"]: n for n in node_objs}
            edges: List[Dict[str, Any]] = []
            for r in rels[:400]:
                s = by_name.get(r.get("source"))
                t = by_name.get(r.get("target"))
                if s and t:
                    edges.append(
                        {
                            "id": str(uuid.uuid4()),
                            "source_id": s["id"],
                            "target_id": t["id"],
                            "relation": r.get("type", "RELATED_TO"),
                            "confidence": float(r.get("confidence", 0.7)),
                        }
                    )
            return ExtractionResult(nodes=node_objs, edges=edges, reasoning="Gemini extraction")
        except Exception:
            logger.exception("llm_extraction_failed – fallback to heuristic")
            return self._heuristic_extract(text)

    def _heuristic_extract(self, text: str) -> ExtractionResult:
        capitals = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", text)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        keywords = re.findall(r"\b(gradient|descent|optimization|algorithm|parameters|mini-batch|batch|stochastic|momentum)\b", text, flags=re.IGNORECASE)
        raw = capitals + acronyms + [k.lower() for k in keywords]
        seen: Dict[str, bool] = {}
        ordered: List[str] = []
        for w in raw:
            if w and w not in seen:
                seen[w] = True
                ordered.append(w)
        ordered = ordered[:80]
        nodes = [
            {"id": str(uuid.uuid4()), "label": "Entity", "name": w, "properties": {"source": "heuristic"}}
            for w in ordered
        ]
        edges: List[Dict[str, Any]] = []
        for i in range(len(nodes) - 1):
            edges.append(
                {
                    "id": str(uuid.uuid4()),
                    "source_id": nodes[i]["id"],
                    "target_id": nodes[i + 1]["id"],
                    "relation": "RELATED_TO",
                    "confidence": 0.35,
                }
            )
        return ExtractionResult(nodes=nodes, edges=edges, reasoning="Heuristic extraction")

    # ---------------------- Embeddings ----------------------
    async def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for t in texts:
            if t in self.embedding_cache:
                out.append(self.embedding_cache[t])
                continue
            if not gemini_client.is_configured():  # type: ignore[attr-defined]
                vec: List[float] = []
            else:
                try:
                    vec = await gemini_client.embed_text(t)  # type: ignore
                except Exception:
                    logger.warning("embedding_failed len=%d", len(t))
                    vec = []
            self.embedding_cache[t] = vec
            out.append(vec)
        return out

    def _chunk_text(self, text: str, max_tokens: int = 600) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        token_est = 0
        for para in text.split("\n"):
            p = para.strip()
            if not p:
                continue
            tokens = len(p) // 4 + 1
            if token_est + tokens > max_tokens and current:
                parts.append(" \n".join(current))
                current = [p]
                token_est = tokens
            else:
                current.append(p)
                token_est += tokens
        if current:
            parts.append(" \n".join(current))
        return parts[:100]

    # ---------------------- Ingestion ----------------------
    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        force_heuristic: bool = False,
        disable_embeddings: bool = False,
        namespace: Optional[str] = None,
    compute_layout: bool = True,
    ) -> Dict[str, Any]:
        # Feature flag (Phase 6 prep): if GraphRAG disabled OR default ingest mode not graphrag, still allow legacy path? For now we gate entirely.
        if not self.enabled and settings.DEFAULT_INGEST_MODE != 'graphrag':
            return {"success": False, "error": "GraphRAG disabled"}
        t_start = time.perf_counter()
        ns = namespace or settings.DEFAULT_NAMESPACE
        try:
            # Advanced section + chunk parsing (creates semantic sections)
            chunks, section_map = self._split_sections_and_chunks(text)
            extraction = (
                self._heuristic_extract(text)
                if force_heuristic
                else await self.extract_entities_and_relations(text)
            )
            # Lightweight in-process classification enrichment (Technology / Organization / Role / Achievement)
            self._classify_enrich_entities(extraction)
            if not extraction.nodes:
                # Additional fallback: capture multi-word proper noun phrases
                import re
                phrases = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b", text)
                uniq: Dict[str,bool] = {}
                new_nodes: List[Dict[str,Any]] = []
                for ph in phrases:
                    if len(ph) < 3: continue
                    k = ph.lower()
                    if k in uniq: continue
                    uniq[k] = True
                    new_nodes.append({"id": str(uuid.uuid4()), "label": "Entity", "name": ph.strip(), "properties": {"source": "fallback-phrase"}})
                    if len(new_nodes) >= 50:
                        break
                if new_nodes:
                    extraction = ExtractionResult(nodes=new_nodes, edges=[], reasoning=extraction.reasoning+" + fallback phrases")
            upsert_stats = await self._upsert_graph_full(
                doc_id,
                chunks,
                extraction,
                disable_embeddings=disable_embeddings,
                namespace=ns,
                section_map=section_map,
                compute_layout=compute_layout,
            )
            # Phase 5: update ingest log (hash-based change detection placeholder)
            try:
                content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                from app.models.database import IngestLog  # lazy import
                from sqlalchemy import select, update
                async with get_db_session() as session:
                    existing_q = await session.execute(select(IngestLog).where(IngestLog.id == doc_id, IngestLog.namespace == ns))
                    row = existing_q.scalars().first()
                    if row:
                        # mark stale if hash changed
                        if row.content_hash != content_hash:
                            row.content_hash = content_hash
                            row.status = 'stale'
                            row.meta = (row.meta or {})
                            row.meta['prev_hash'] = row.meta.get('prev_hash', []) + [row.content_hash]
                    else:
                        session.add(IngestLog(id=doc_id, namespace=ns, content_hash=content_hash, status='ingested', meta=metadata or {}))
                    await session.commit()
            except Exception:
                logger.debug("ingest_log_update_failed", exc_info=True)
            self.metrics["ingest_count"] += 1
            self.metrics["edges_created"] += upsert_stats.get("edges", 0)
            nd = self.metrics["namespace_docs"]
            nd[ns] = nd.get(ns, 0) + 1
            return {
                "success": True,
                "extraction": extraction.reasoning,
                "stats": upsert_stats,
                "namespace": ns,
            }
        except Exception as e:
            logger.exception("ingest_failed doc_id=%s", doc_id)
            return {"success": False, "error": str(e)}
        finally:
            dur = time.perf_counter() - t_start
            self.metrics["ingest_latency_sum"] += dur
            self.metrics["ingest_latency_count"] += 1

    def _split_sections_and_chunks(self, text: str, max_tokens: int = 450) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Split document into (section-aware) chunks.
        Returns (chunks, section_map) where section_map aligns with chunks list indices:
          section_map[i] = { 'section_id', 'section_title', 'local_index' }
        Simple heuristic: lines in ALL CAPS or Title Case followed by blank line start a new section.
        """
        import re, unicodedata
        lines = text.splitlines()
        sections: List[Tuple[str, List[str]]] = []
        current_title = "Root"
        current_buf: List[str] = []
        section_title_pattern = re.compile(r"^([A-Z][A-Z\s/&+-]{2,}|[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,5})\s*$")
        def flush():
            nonlocal current_title, current_buf
            if current_buf:
                sections.append((current_title.strip(), current_buf))
                current_buf = []
        for ln in lines:
            raw = ln.strip()
            if not raw:
                current_buf.append(ln)
                continue
            if section_title_pattern.match(raw) and len(raw.split()) <= 8:
                flush()
                current_title = raw.title()
                continue
            current_buf.append(ln)
        flush()
        # Now chunk within each section
        all_chunks: List[str] = []
        section_map: List[Dict[str, Any]] = []
        global_idx = 0
        for title, raw_lines in sections:
            body = "\n".join([l for l in raw_lines if l.strip()])
            if not body.strip():
                continue
            # break body into paragraph groups under token cap
            parts: List[str] = []
            cur: List[str] = []
            tok_est = 0
            for para in body.split("\n"):
                p = para.strip()
                if not p:
                    continue
                tks = len(p)//4 + 1
                if tok_est + tks > max_tokens and cur:
                    parts.append(" \n".join(cur))
                    cur = [p]
                    tok_est = tks
                else:
                    cur.append(p)
                    tok_est += tks
            if cur:
                parts.append(" \n".join(cur))
            # register chunks
            slug = re.sub(r"[^a-z0-9]+","-", title.lower()).strip('-') or "section"
            for local_i, ck in enumerate(parts):
                all_chunks.append(ck)
                section_map.append({
                    "section_id": f"{slug}",
                    "section_title": title,
                    "local_index": local_i,
                    "global_index": global_idx,
                })
                global_idx += 1
        if not all_chunks:
            # fallback to legacy behavior
            return self._chunk_text(text), []
        return all_chunks, section_map

    async def _upsert_graph_full(
        self,
        doc_id: str,
        chunks: List[str],
        extraction: ExtractionResult,
        *,
        disable_embeddings: bool = False,
        namespace: str = "public",
        section_map: Optional[List[Dict[str, Any]]] = None,
        compute_layout: bool = True,
    ) -> Dict[str, int]:
        # Neo4j path
        if self.graph_store == "neo4j" and self.neo4j_driver:
            try:
                chunk_nodes = [
                    {
                        "id": f"{doc_id}::chunk::{idx}",
                        "label": "Chunk",
                        "name": f"Chunk {idx}",
                        "properties": {
                            "doc_id": doc_id,
                            "chunk_index": idx,
                            "text": chunk,
                            "namespace": namespace,
                        },
                    }
                    for idx, chunk in enumerate(chunks)
                ]
                entity_nodes = []
                for n in extraction.nodes:
                    entity_nodes.append(
                        {
                            "id": n.get("id", str(uuid.uuid4())),
                            "label": n.get("label", "Entity"),
                            "name": n.get("name", "Unnamed"),
                            "properties": {**n.get("properties", {}), "namespace": namespace},
                        }
                    )
                edges: List[Dict[str, Any]] = []
                for e in extraction.edges:
                    edges.append(
                        {
                            "id": e.get("id", str(uuid.uuid4())),
                            "source_id": e.get("source_id") or e.get("source") or e.get("source_name"),
                            "target_id": e.get("target_id") or e.get("target") or e.get("target_name"),
                            "relation": e.get("relation", "RELATED_TO"),
                            "confidence": float(e.get("confidence", 0.7)),
                        }
                    )
                lowered_chunks = [c.lower() for c in chunks]
                for en in entity_nodes[:300]:
                    lname = en["name"].lower()
                    hits: List[int] = []
                    for idx, lc in enumerate(lowered_chunks):
                        if lname and lname in lc:
                            hits.append(idx)
                            if len(hits) >= 5:
                                break
                    for idx in hits:
                        edges.append(
                            {
                                "id": str(uuid.uuid4()),
                                "source_id": en["id"],
                                "target_id": f"{doc_id}::chunk::{idx}",
                                "relation": "MENTIONED_IN",
                                "confidence": 0.6,
                            }
                        )
                async with self.neo4j_driver.session() as session:  # type: ignore
                    await session.execute_write(
                        lambda tx, nodes: tx.run(
                            """
                            UNWIND $nodes AS n
                            MERGE (x {id: n.id})
                            SET x += n.properties, x.name = n.name, x.label = n.label
                            """,
                            nodes=[{**n, "properties": n.get("properties", {})} for n in chunk_nodes + entity_nodes],
                        ),
                        chunk_nodes + entity_nodes,
                    )
                    name_to_id = {n["name"]: n["id"] for n in chunk_nodes + entity_nodes}
                    norm_edges = []
                    for e in edges:
                        s = name_to_id.get(e["source_id"], e["source_id"])
                        t = name_to_id.get(e["target_id"], e["target_id"])
                        if s and t:
                            norm_edges.append({**e, "source_id": s, "target_id": t})
                    await session.execute_write(
                        lambda tx, es: tx.run(
                            """
                            UNWIND $edges AS e
                            MATCH (s {id: e.source_id})
                            MATCH (t {id: e.target_id})
                            MERGE (s)-[r:REL {id: e.id}]->(t)
                            SET r.relation = e.relation, r.confidence = e.confidence
                            """,
                            edges=es,
                        ),
                        norm_edges,
                    )
                return {"nodes": len(chunk_nodes) + len(entity_nodes), "edges": len(edges), "store": "neo4j"}
            except Exception:
                logger.exception("neo4j_upsert_failed")
                return {"nodes": len(extraction.nodes), "edges": len(extraction.edges), "store": "neo4j:error"}

        # SQLite path
        created_nodes = 0
        created_edges = 0
        async with get_db_session() as session:
            assert isinstance(session, AsyncSession)
            try:
                # Idempotency safety: purge existing chunk/section nodes & their edges for this doc_id (re-ingest / update path)
                try:
                    from sqlalchemy import delete, or_, and_
                    await session.execute(
                        delete(GraphEdge).where(
                            or_(
                                GraphEdge.source_id.like(f"{doc_id}::chunk::%"),
                                GraphEdge.target_id.like(f"{doc_id}::chunk::%"),
                                GraphEdge.source_id.like(f"{doc_id}::section::%"),
                                GraphEdge.target_id.like(f"{doc_id}::section::%"),
                            )
                        )
                    )
                    await session.execute(
                        delete(GraphNode).where(
                            or_(
                                GraphNode.id.like(f"{doc_id}::chunk::%"),
                                GraphNode.id.like(f"{doc_id}::section::%"),
                            )
                        )
                    )
                except Exception:
                    logger.debug("doc_purge_failed doc_id=%s", doc_id, exc_info=True)
                # Chunk nodes
                chunk_nodes: List[GraphNode] = []
                first_emb_dim: Optional[int] = None
                for idx, chunk in enumerate(chunks):
                    node_id = f"{doc_id}::chunk::{idx}"
                    emb: List[float] = []
                    if not disable_embeddings:
                        embs = await self._embed_texts([chunk])
                        emb = embs[0] if embs else []
                        if emb and first_emb_dim is None:
                            first_emb_dim = len(emb)
                    props = {"doc_id": doc_id, "chunk_index": idx, "namespace": namespace, "text": chunk}
                    if section_map and idx < len(section_map):
                        props.update({
                            "section_id": section_map[idx]["section_id"],
                            "section_title": section_map[idx]["section_title"],
                            "section_local_index": section_map[idx]["local_index"],
                        })
                    gn = GraphNode(
                        id=node_id,
                        label="Chunk",
                        name=f"Chunk {idx}",
                        properties=props,
                        source_ids=[doc_id],
                        embedding=emb,
                        namespace=namespace,
                    )
                    session.add(gn)
                    chunk_nodes.append(gn)
                    created_nodes += 1

                # Entity nodes (dedupe by name + namespace)
                existing_q = await session.execute(select(GraphNode))
                existing_nodes = existing_q.scalars().all()
                existing_lookup = {
                    (n.name.lower(), (n.properties or {}).get("namespace")): n for n in existing_nodes
                }
                entity_name_to_id: Dict[str, str] = {}
                for n in extraction.nodes:
                    nm = n.get("name", "Unnamed")
                    key = (nm.lower(), namespace)
                    if key in existing_lookup:
                        entity_name_to_id[nm] = existing_lookup[key].id
                        continue
                    emb: List[float] = []
                    if not disable_embeddings and nm:
                        embs = await self._embed_texts([nm])
                        emb = embs[0] if embs else []
                        if emb and first_emb_dim is None:
                            first_emb_dim = len(emb)
                    node_id = n.get("id", str(uuid.uuid4()))
                    gn = GraphNode(
                        id=node_id,
                        label=n.get("label", "Entity"),
                        name=nm,
                        properties={**n.get("properties", {}), "namespace": namespace},
                        source_ids=[doc_id],
                        embedding=emb,
                        namespace=namespace,
                    )
                    session.add(gn)
                    entity_name_to_id[nm] = node_id
                    created_nodes += 1

                # Edges
                for e in extraction.edges:
                    sid = e.get("source_id") or e.get("source") or e.get("source_name")
                    tid = e.get("target_id") or e.get("target") or e.get("target_name")
                    sid = entity_name_to_id.get(sid, sid)
                    tid = entity_name_to_id.get(tid, tid)
                    if not sid or not tid:
                        continue
                    ge = GraphEdge(
                        id=e.get("id", str(uuid.uuid4())),
                        source_id=sid,
                        target_id=tid,
                        relation=e.get("relation", "RELATED_TO"),
                        confidence=float(e.get("confidence", 0.7)),
                        properties={"namespace": namespace},
                    )
                    session.add(ge)
                    created_edges += 1

                # Section nodes & containment edges
                section_id_map: Dict[str, str] = {}
                if section_map:
                    for meta in section_map:
                        sid_raw = meta["section_id"]
                        # stable section node id
                        sec_node_id = f"{doc_id}::section::{sid_raw}"
                        # De-dup within a single ingest: check by raw section key
                        if sid_raw in section_id_map:
                            continue
                        section_id_map[sid_raw] = sec_node_id
                        sec_node = GraphNode(
                            id=sec_node_id,
                            label="Section",
                            name=meta["section_title"][:100],
                            properties={"doc_id": doc_id, "namespace": namespace, "section_id": sid_raw, "title": meta["section_title"]},
                            source_ids=[doc_id],
                            embedding=[],
                            namespace=namespace,
                        )
                        session.add(sec_node)
                        created_nodes += 1
                    # link chunks to their section
                    for idx, meta in enumerate(section_map):
                        sec_node_id = section_id_map.get(meta["section_id"])
                        if not sec_node_id:
                            continue
                        ge = GraphEdge(
                            id=str(uuid.uuid4()),
                            source_id=sec_node_id,
                            target_id=f"{doc_id}::chunk::{idx}",
                            relation="CONTAINS",
                            confidence=0.9,
                            properties={"namespace": namespace},
                        )
                        session.add(ge)
                        created_edges += 1

                # Mention edges already created; build map chunk -> entities mentioned
                chunk_entity_map: Dict[int, List[str]] = {}
                if section_map:
                    # derive from mention edges we just added (in lowered_chunks pass) by scanning session new objects
                    # easier: re-run mention detection quickly
                    lowered_chunks = [c.lower() for c in chunks]
                    for en_name, en_id in entity_name_to_id.items():
                        lname = en_name.lower()
                        if not lname:
                            continue
                        for idx, lc in enumerate(lowered_chunks):
                            if lname in lc:
                                chunk_entity_map.setdefault(idx, []).append(en_id)
                # Co-occurrence edges between entities within same chunk
                added_pairs: Set[Tuple[str, str]] = set()
                for ents in chunk_entity_map.values():
                    uniq = list(dict.fromkeys(ents))
                    for i in range(len(uniq)):
                        for j in range(i+1, len(uniq)):
                            a, b = sorted([uniq[i], uniq[j]])
                            key = (a,b)
                            if key in added_pairs:
                                continue
                            added_pairs.add(key)
                            ge = GraphEdge(
                                id=str(uuid.uuid4()),
                                source_id=a,
                                target_id=b,
                                relation="CO_OCCURS",
                                confidence=0.55,
                                properties={"namespace": namespace},
                            )
                            session.add(ge)
                            created_edges += 1
                # Section HAS_ENTITY edges
                if section_map and section_id_map:
                    section_entities: Dict[str, Set[str]] = {}
                    for idx, ents in chunk_entity_map.items():
                        if idx < len(section_map):
                            sid = section_map[idx]["section_id"]
                            section_entities.setdefault(sid, set()).update(ents)
                    for sid_raw, ents in section_entities.items():
                        sec_node_id = section_id_map.get(sid_raw)
                        if not sec_node_id:
                            continue
                        for eid in ents:
                            ge = GraphEdge(
                                id=str(uuid.uuid4()),
                                source_id=sec_node_id,
                                target_id=eid,
                                relation="HAS_ENTITY",
                                confidence=0.5,
                                properties={"namespace": namespace},
                            )
                            session.add(ge)
                            created_edges += 1

                # ---------- Derived semantic relations (ROLE_AT, USES_TECH) ----------
                try:
                    # Build quick lookup of entity id -> label
                    entity_label_lookup: Dict[str, str] = {}
                    for n in extraction.nodes:
                        nm = n.get("name")
                        if nm and nm in entity_name_to_id:
                            entity_label_lookup[entity_name_to_id[nm]] = n.get("label", "Entity")
                    # Chunk level inference: if a Role and Organization co-occur => ROLE_AT
                    # If Role or Organization with Technology => USES_TECH
                    rel_added: Set[Tuple[str, str, str]] = set()
                    for ents in chunk_entity_map.values():
                        roles = [e for e in ents if entity_label_lookup.get(e) == "Role"]
                        orgs = [e for e in ents if entity_label_lookup.get(e) == "Organization"]
                        techs = [e for e in ents if entity_label_lookup.get(e) == "Technology"]
                        # ROLE_AT edges
                        for r in roles[:20]:
                            for o in orgs[:20]:
                                key = (r, o, "ROLE_AT")
                                if key in rel_added:
                                    continue
                                rel_added.add(key)
                                ge = GraphEdge(
                                    id=str(uuid.uuid4()),
                                    source_id=r,
                                    target_id=o,
                                    relation="ROLE_AT",
                                    confidence=0.65,
                                    properties={"namespace": namespace},
                                )
                                session.add(ge)
                                created_edges += 1
                        # USES_TECH edges
                        for holder in roles + orgs:
                            for t in techs[:30]:
                                key = (holder, t, "USES_TECH")
                                if key in rel_added:
                                    continue
                                rel_added.add(key)
                                ge = GraphEdge(
                                    id=str(uuid.uuid4()),
                                    source_id=holder,
                                    target_id=t,
                                    relation="USES_TECH",
                                    confidence=0.55,
                                    properties={"namespace": namespace},
                                )
                                session.add(ge)
                                created_edges += 1
                except Exception:
                    logger.warning("semantic_relation_infer_failed", exc_info=True)

                # Mention edges
                lowered_chunks = [c.lower() for c in chunks]
                for en_name, en_id in entity_name_to_id.items():
                    lname = en_name.lower()
                    if not lname:
                        continue
                    hits: List[int] = []
                    for idx, lc in enumerate(lowered_chunks):
                        if lname in lc:
                            hits.append(idx)
                            if len(hits) >= 5:
                                break
                    for idx in hits:
                        ge = GraphEdge(
                            id=str(uuid.uuid4()),
                            source_id=en_id,
                            target_id=f"{doc_id}::chunk::{idx}",
                            relation="MENTIONED_IN",
                            confidence=0.6,
                            properties={"namespace": namespace},
                        )
                        session.add(ge)
                        created_edges += 1

                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("sqlite_upsert_failed")
        # Qdrant upsert (after commit) for nodes with embeddings
        if self.qdrant and not disable_embeddings:
            try:
                from qdrant_client.http import models as qmodels  # type: ignore
                # Need to fetch nodes we just added with embeddings for this doc
                async with get_db_session() as session:
                    q = await session.execute(select(GraphNode).where(GraphNode.source_ids.contains([doc_id])))  # type: ignore
                    doc_nodes = [n for n in q.scalars().all() if isinstance(n.embedding, list) and n.embedding]
                if doc_nodes:
                    self._ensure_qdrant_collection(len(doc_nodes[0].embedding))
                    points = []
                    for n in doc_nodes:
                        points.append(
                            qmodels.PointStruct(  # type: ignore
                                id=self._stable_int_id(n.id),
                                vector=n.embedding,
                                payload={
                                    "node_id": n.id,
                                    "label": n.label,
                                    "namespace": (n.properties or {}).get("namespace"),
                                    "doc_id": (n.properties or {}).get("doc_id"),
                                },
                            )
                        )
                    if points:
                        self.qdrant.upsert(collection_name=self._qdrant_collection, points=points)  # type: ignore
            except Exception:
                logger.warning("qdrant_upsert_failed doc_id=%s", doc_id)
        # Streaming broadcast (Phase 7): notify subscribers of newly added nodes/edges
        try:
            from app.api import smart_assistant  # type: ignore
            subs = getattr(smart_assistant, "_graphrag_stream_subs", [])
            if subs:
                import asyncio
                new_events: List[Dict[str, Any]] = []
                for cn in chunk_nodes:
                    new_events.append({"event": "node_added", "data": {"id": cn.id, "label": cn.label, "name": cn.name}})
                # entity_name_to_id contains all entity names; we only have IDs for newly created ones above
                # To reduce overhead we skip per-edge events and send a summary
                if created_edges:
                    new_events.append({"event": "edges_added", "data": {"count": created_edges, "doc_id": doc_id}})
                async def _push(evts: List[Dict[str, Any]]):
                    for evt in evts:
                        for q in list(subs):
                            try:
                                q.put_nowait(evt)
                            except Exception:
                                pass
                asyncio.create_task(_push(new_events))
        except Exception:
            pass
        # Compute layout post-commit
        if compute_layout:
            try:
                await self._compute_and_store_layout(namespace)
            except Exception:
                logger.warning("layout_compute_failed", exc_info=True)
        return {"nodes": created_nodes, "edges": created_edges, "store": "sqlite"}

    async def _compute_and_store_layout(self, namespace: str) -> None:
        from sqlalchemy import select
        from app.core.database import get_db_session
        from app.models.database import GraphNode, GraphEdge
        import networkx as nx
        async with get_db_session() as session:
            nres = await session.execute(select(GraphNode))
            nodes = [n for n in nres.scalars().all() if (n.properties or {}).get("namespace") == namespace]
            if not nodes:
                return
            eres = await session.execute(select(GraphEdge))
            edges = [e for e in eres.scalars().all() if (e.properties or {}).get("namespace") == namespace]
            G = nx.Graph()
            for e in edges:
                G.add_edge(e.source_id, e.target_id, relation=e.relation)
            for n in nodes:
                if n.id not in G:
                    G.add_node(n.id)
            # Hybrid deterministic layout: place Section nodes radially, then run spring layout initialized near those anchors for others.
            sections = [n for n in nodes if n.label == "Section"]
            section_positions: Dict[str, Tuple[float,float]] = {}
            if sections:
                radius = 1.0 + math.log(len(sections)+1)*0.2
                for i, s in enumerate(sections):
                    angle = (2*math.pi * i) / max(1,len(sections))
                    section_positions[s.id] = (radius*math.cos(angle), radius*math.sin(angle))
            # Initial positions
            init_pos: Dict[str, Tuple[float,float]] = {}
            for n in nodes:
                if n.id in section_positions:
                    init_pos[n.id] = section_positions[n.id]
                else:
                    # If chunk inside a section, bias near section
                    sec_id = (n.properties or {}).get("section_id")
                    if sec_id:
                        # convert to section node id pattern used earlier
                        candidate = f"{(n.properties or {}).get('doc_id','doc')}::section::{sec_id}"
                        anchor = section_positions.get(candidate)
                        if anchor:
                            jitter = (math.sin(hash(n.id)%100/100*2*math.pi)*0.15, math.cos(hash(n.id)%100/100*2*math.pi)*0.15)
                            init_pos[n.id] = (anchor[0] + jitter[0], anchor[1] + jitter[1])
                            continue
                    # fallback random small circle
                    init_pos[n.id] = (math.cos(hash(n.id)%360/180*math.pi)*0.5, math.sin(hash(n.id)%360/180*math.pi)*0.5)
            try:
                pos = nx.spring_layout(
                    G,
                    k=0.6 / (max(len(G.nodes()),1)**0.5),
                    iterations=40,
                    seed=42,
                    pos=init_pos,
                    weight=None,
                )
            except Exception:
                pos = init_pos  # fallback
            # Degree-based sizing metadata
            degrees = dict(G.degree())
            max_deg = max(degrees.values()) if degrees else 1
            for n in nodes:
                n.properties = (n.properties or {})
                layout = n.properties.get("layout", {})
                p = pos.get(n.id, (0.0, 0.0))
                layout.update({"x": float(p[0]), "y": float(p[1])})
                n.properties["layout"] = layout
                n.properties["degree"] = int(degrees.get(n.id, 0))
                if max_deg:
                    n.properties["degree_norm"] = round(degrees.get(n.id, 0) / max_deg, 4)
            await session.commit()

    async def recompute_layout(self, namespace: Optional[str] = None, mode: str = "hybrid") -> Dict[str, Any]:
        """Public method to recompute and persist layout.
        mode: 'hybrid' (default) uses section anchors + spring
              'clustered' groups by Louvain clusters (if available) and spaces clusters, then springs inside each cluster.
        """
        ns = namespace or settings.DEFAULT_NAMESPACE
        if mode == "hybrid":
            await self._compute_and_store_layout(ns)
            return {"success": True, "mode": mode}
        # clustered mode
        try:
            import networkx as nx
            from sqlalchemy import select
            from app.core.database import get_db_session
            from app.models.database import GraphNode, GraphEdge, GraphClusterMembership
            async with get_db_session() as session:
                nres = await session.execute(select(GraphNode))
                nodes = [n for n in nres.scalars().all() if (n.properties or {}).get("namespace") == ns]
                if not nodes:
                    return {"success": False, "error": "no nodes"}
                eres = await session.execute(select(GraphEdge))
                edges = [e for e in eres.scalars().all() if (e.properties or {}).get("namespace") == ns]
                mres = await session.execute(select(GraphClusterMembership))
                memberships = [m for m in mres.scalars().all() if m.namespace == ns]
                cluster_map: Dict[str, List[str]] = {}
                for m in memberships:
                    cluster_map.setdefault(m.cluster_id, []).append(m.node_id)
                if not cluster_map:
                    # fallback to hybrid
                    await self._compute_and_store_layout(ns)
                    return {"success": True, "mode": "hybrid-fallback"}
                G = nx.Graph()
                for e in edges:
                    G.add_edge(e.source_id, e.target_id)
                for n in nodes:
                    if n.id not in G:
                        G.add_node(n.id)
                # Arrange clusters on circle
                cluster_ids = sorted(cluster_map.keys())
                R = 4.0 + math.log(len(cluster_ids)+1)
                cluster_centers: Dict[str, Tuple[float,float]] = {}
                for i, cid in enumerate(cluster_ids):
                    angle = 2*math.pi*i/len(cluster_ids)
                    cluster_centers[cid] = (R*math.cos(angle), R*math.sin(angle))
                # For each cluster run mini spring
                for cid, node_ids in cluster_map.items():
                    sub = G.subgraph(node_ids)
                    if len(sub.nodes()) == 1:
                        # place single node at center
                        nid = list(sub.nodes())[0]
                        p = cluster_centers[cid]
                        for n in nodes:
                            if n.id == nid:
                                n.properties = (n.properties or {})
                                lay = n.properties.get("layout", {})
                                lay.update({"x": p[0], "y": p[1]})
                                n.properties["layout"] = lay
                        continue
                    try:
                        sub_pos = nx.spring_layout(sub, k=0.4/(len(sub.nodes())**0.5), iterations=35, seed=42)
                    except Exception:
                        sub_pos = {nid: (math.cos(i), math.sin(i)) for i, nid in enumerate(sub.nodes())}
                    cx, cy = cluster_centers[cid]
                    # scale cluster to radius
                    scale = 1.2 + math.log(len(sub.nodes())+1)*0.15
                    for nid, (xv,yv) in sub_pos.items():
                        for n in nodes:
                            if n.id == nid:
                                n.properties = (n.properties or {})
                                lay = n.properties.get("layout", {})
                                lay.update({"x": cx + xv*scale, "y": cy + yv*scale})
                                n.properties["layout"] = lay
                # compute degrees & normalize
                degrees = dict(G.degree())
                max_deg = max(degrees.values()) if degrees else 1
                for n in nodes:
                    n.properties = (n.properties or {})
                    n.properties["degree"] = int(degrees.get(n.id,0))
                    n.properties["degree_norm"] = round((degrees.get(n.id,0)/max_deg) if max_deg else 0,4)
                await session.commit()
            return {"success": True, "mode": mode, "clusters": len(cluster_ids)}
        except Exception as e:
            logger.warning("clustered_layout_failed", exc_info=True)
            return {"success": False, "error": str(e)}

    # ---------------------- Centrality Computation ----------------------
    async def compute_centrality(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Compute centrality metrics (PageRank, Betweenness) and persist on nodes.
        Stores raw + normalized values and an aggregate 'importance' heuristic used by UI.
        """
        ns = namespace or settings.DEFAULT_NAMESPACE
        try:
            import networkx as nx
            from sqlalchemy import select
            from app.core.database import get_db_session
            from app.models.database import GraphNode, GraphEdge
            async with get_db_session() as session:
                nres = await session.execute(select(GraphNode))
                nodes = [n for n in nres.scalars().all() if (n.properties or {}).get("namespace") == ns]
                if not nodes:
                    return {"success": False, "error": "no nodes"}
                eres = await session.execute(select(GraphEdge))
                edges = [e for e in eres.scalars().all() if (e.properties or {}).get("namespace") == ns]
                G = nx.Graph()
                for e in edges:
                    G.add_edge(e.source_id, e.target_id)
                for n in nodes:
                    if n.id not in G:
                        G.add_node(n.id)
                # Compute centralities (guard size for betweenness cost)
                pr: Dict[str, float] = {}
                btw: Dict[str, float] = {}
                try:
                    pr = nx.pagerank(G, max_iter=100, alpha=0.85) if G.number_of_nodes() <= 5000 else {}
                except Exception:
                    logger.warning("pagerank_failed", exc_info=True)
                try:
                    if G.number_of_nodes() <= 1200:
                        btw = nx.betweenness_centrality(G, k=None, normalized=True)
                    elif G.number_of_nodes() <= 8000:
                        # sample-based approximation for larger graphs
                        k = max(10, int(G.number_of_nodes() * 0.02))
                        btw = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)
                except Exception:
                    logger.warning("betweenness_failed", exc_info=True)
                # Normalization helpers
                def norm(d: Dict[str, float]) -> Dict[str, float]:
                    if not d:
                        return {}
                    vals = list(d.values())
                    mn, mx = min(vals), max(vals)
                    if mx - mn < 1e-12:
                        return {k: 0.0 for k in d}
                    return {k: (v - mn) / (mx - mn) for k, v in d.items()}
                pr_norm = norm(pr)
                btw_norm = norm(btw)
                updated = 0
                for n in nodes:
                    n.properties = (n.properties or {})
                    if n.id in pr:
                        n.properties["pagerank"] = round(pr[n.id], 8)
                        n.properties["pagerank_norm"] = round(pr_norm.get(n.id, 0.0), 6)
                    if n.id in btw:
                        n.properties["betweenness"] = round(btw[n.id], 8)
                        n.properties["betweenness_norm"] = round(btw_norm.get(n.id, 0.0), 6)
                    # Importance heuristic: average of available normalized metrics (degree_norm already present often)
                    degn = n.properties.get("degree_norm")
                    parts = []
                    for key in ["pagerank_norm", "betweenness_norm", "degree_norm"]:
                        v = n.properties.get(key)
                        if isinstance(v, (int, float)):
                            parts.append(float(v))
                    if parts:
                        n.properties["importance"] = round(sum(parts) / len(parts), 6)
                        updated += 1
                await session.commit()
                return {"success": True, "nodes_updated": updated, "have_pagerank": bool(pr), "have_betweenness": bool(btw)}
        except Exception as e:
            logger.warning("centrality_compute_failed", exc_info=True)
            return {"success": False, "error": str(e)}

    # ---------------------- Classification Enrichment ----------------------
    def _classify_enrich_entities(self, extraction: ExtractionResult) -> None:
        """Mutate extraction.nodes in-place assigning more specific labels using heuristics.
        Adds: Technology, Organization, Role, Achievement.
        """
        tech_keywords = {
            "python","typescript","javascript","react","vue","angular","docker","kubernetes","aws","gcp","azure","postgres","mysql","sqlite","redis","kafka","spark","airflow","pytorch","tensorflow","llm","transformer","langchain","openai","neo4j","graph","k8s","helm","terraform","ansible","sql","graphql","fastapi","django","flask","pandas","numpy","scikit","sklearn","hadoop","elastic","elasticsearch"
        }
        org_suffixes = ["inc","corp","corporation","llc","l.l.c","ltd","company","university","labs","institute","systems"]
        org_keywords = {"google","microsoft","amazon","openai","meta","ibm","oracle","netflix","apple","nvidia","intel","salesforce"}
        role_keywords = ["engineer","developer","scientist","manager","lead","architect","director","specialist","analyst","researcher","consultant","founder","cto","ceo","head","principal"]
        achievement_keywords = ["award","patent","publication","certified","certification","speaker","presented","keynote"]
        for n in extraction.nodes:
            name = n.get("name") or ""
            base = name.lower().strip()
            label = n.get("label") or "Entity"
            # Technology
            if any(k in base for k in tech_keywords):
                label = "Technology"
            # Organization heuristic: multi word capitalized or suffix / keyword
            words = re.findall(r"[A-Za-z0-9&]+", name)
            if label == "Entity":
                if (len(words) >= 2 and all(w[0].isupper() for w in words[:2])) or any(base.endswith(s) for s in org_suffixes) or base in org_keywords:
                    label = "Organization"
            # Role
            if label == "Entity" and any(r in base for r in role_keywords):
                label = "Role"
            # Achievement
            if label == "Entity" and any(a in base for a in achievement_keywords):
                label = "Achievement"
            n["label"] = label

    # ---------------------- Retrieval ----------------------
    async def hybrid_retrieve(
        self,
        query: str,
        top_k: int = 5,
        *,
        namespace: Optional[str] = None,
        label_filter: Optional[List[str]] = None,
        relation_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        self.metrics["retrieval_requests"] += 1
        t0 = time.perf_counter()
        ns = namespace or settings.DEFAULT_NAMESPACE
        results: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        strategy_chain: List[str] = []
        async with get_db_session() as session:
            assert isinstance(session, AsyncSession)
            try:
                # Qdrant vector search first (if available)
                chosen: List[GraphNode] = []
                if self.qdrant and gemini_client.is_configured():  # type: ignore[attr-defined]
                    try:
                        q_emb = await self._embed_texts([query])
                        if q_emb and q_emb[0]:
                            from qdrant_client.http import models as qmodels  # type: ignore
                            flt = qmodels.Filter(  # type: ignore
                                must=[
                                    qmodels.FieldCondition(  # type: ignore
                                        key="namespace", match=qmodels.MatchValue(value=ns)  # type: ignore
                                    )
                                ]
                            )
                            q_results = self.qdrant.search(  # type: ignore
                                collection_name=self._qdrant_collection,
                                query_vector=q_emb[0],
                                limit=top_k * 3,
                                query_filter=flt,
                            )
                            node_ids = [r.payload.get("node_id") for r in q_results if r and r.payload]
                            node_ids = [nid for nid in node_ids if nid]
                            if node_ids:
                                db_nodes_q = await session.execute(
                                    select(GraphNode).where(GraphNode.id.in_(node_ids))
                                )
                                fetched = db_nodes_q.scalars().all()
                                if label_filter:
                                    fetched = [n for n in fetched if n.label in label_filter]
                                # Preserve Qdrant order
                                id_rank = {nid: i for i, nid in enumerate(node_ids)}
                                fetched.sort(key=lambda n: id_rank.get(n.id, 10**9))
                                chosen = fetched[:top_k]
                                if chosen:
                                    strategy_chain.append("qdrant")
                    except Exception:
                        logger.warning("qdrant_search_failed")

                sel = select(GraphNode).limit(1500)
                nodes_q = await session.execute(sel)
                all_nodes = [
                    n
                    for n in nodes_q.scalars().all()
                    if (n.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns
                ]
                if label_filter:
                    all_nodes = [n for n in all_nodes if n.label in label_filter]
                has_embeds = any(isinstance(n.embedding, list) and n.embedding for n in all_nodes)
                # Embedding (in-process) similarity if Qdrant not used or returned nothing
                if has_embeds:
                    if not chosen:
                        q_emb = await self._embed_texts([query])
                    else:
                        q_emb = []  # already embedded
                    if not chosen and q_emb and q_emb[0]:
                        def cosine(a: List[float], b: List[float]) -> float:
                            s = sum(x * y for x, y in zip(a, b))
                            na = math.sqrt(sum(x * x for x in a)) or 1.0
                            nb = math.sqrt(sum(y * y for y in b)) or 1.0
                            return s / (na * nb + 1e-9)
                        scored = [
                            (n, cosine(n.embedding, q_emb[0]))
                            for n in all_nodes
                            if isinstance(n.embedding, list) and n.embedding
                        ]
                        scored.sort(key=lambda x: x[1], reverse=True)
                        if not chosen:
                            chosen = [n for n, _ in scored[:top_k]]
                            if chosen:
                                strategy_chain.append("embedding")

                if not chosen:
                    name_q = await session.execute(
                        select(GraphNode).where(GraphNode.name.ilike(f"%{query}%")).limit(top_k * 5)
                    )
                    name_nodes = [
                        n
                        for n in name_q.scalars().all()
                        if (n.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns
                    ]
                    if label_filter:
                        name_nodes = [n for n in name_nodes if n.label in label_filter]
                    chosen = name_nodes[:top_k]
                    if chosen:
                        strategy_chain.append("name_contains")

                if not chosen:
                    terms = [t.lower() for t in re.findall(r"\w+", query) if t]
                    if terms:
                        chunk_q = await session.execute(
                            select(GraphNode).where(GraphNode.label == "Chunk").limit(4000)
                        )
                        chunks_all: List[GraphNode] = [
                            c
                            for c in chunk_q.scalars().all()
                            if (c.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns
                        ]
                        doc_texts: List[Tuple[GraphNode, List[str]]] = []
                        df: Dict[str, int] = {}
                        for c in chunks_all:
                            txt_raw = (c.properties or {}).get("text", "")
                            toks = [w.lower() for w in re.findall(r"\w+", txt_raw) if w]
                            if not toks:
                                continue
                            doc_texts.append((c, toks))
                            for ut in set(toks):
                                df[ut] = df.get(ut, 0) + 1
                        N = len(doc_texts) or 1
                        avg_dl = sum(len(toks) for _, toks in doc_texts) / N
                        k1 = 1.5
                        b = 0.75
                        scores: List[Tuple[GraphNode, float]] = []
                        term_set = set(terms)
                        for c, toks in doc_texts:
                            dl = len(toks)
                            tf_counts: Dict[str, int] = {}
                            for w in toks:
                                if w in term_set:
                                    tf_counts[w] = tf_counts.get(w, 0) + 1
                            if not tf_counts:
                                continue
                            score = 0.0
                            for term, tf in tf_counts.items():
                                df_t = df.get(term, 0)
                                idf = math.log((N - df_t + 0.5) / (df_t + 0.5) + 1.0)
                                denom = tf + k1 * (1 - b + b * (dl / (avg_dl or 1.0)))
                                score += idf * (tf * (k1 + 1)) / (denom + 1e-9)
                            if score > 0:
                                scores.append((c, score))
                        scores.sort(key=lambda x: x[1], reverse=True)
                        chosen = [n for n, _ in scores[:top_k]]
                        if chosen:
                            strategy_chain.append("bm25")

                for n in chosen:
                    results.append(
                        {
                            "id": n.id,
                            "label": n.label,
                            "name": n.name,
                            "properties": n.properties or {},
                            "source_ids": n.source_ids or [],
                        }
                    )

                if chosen:
                    ids = [n.id for n in chosen]
                    eq = await session.execute(
                        select(GraphEdge).where(
                            (GraphEdge.source_id.in_(ids)) | (GraphEdge.target_id.in_(ids))
                        ).limit(300)
                    )
                    for e in eq.scalars().all():
                        if relation_filter and e.relation not in relation_filter:
                            continue
                        edges.append(
                            {
                                "id": e.id,
                                "source_id": e.source_id,
                                "target_id": e.target_id,
                                "relation": e.relation,
                                "confidence": e.confidence,
                            }
                        )
            except SQLAlchemyError:
                logger.exception("hybrid_retrieve_failed")
        dur = time.perf_counter() - t0
        self.metrics["retrieval_latency_sum"] += dur
        self.metrics["retrieval_latency_count"] += 1
        return {"nodes": results, "edges": edges, "meta": {"strategy": "hybrid", "chain": strategy_chain}}

    # ---------------------- Answer ----------------------
    async def answer(
        self,
        question: str,
        top_k: int = 6,
        *,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.metrics["answer_requests"] += 1
        t0 = time.perf_counter()
        retrieved = await self.hybrid_retrieve(question, top_k=top_k, namespace=namespace)
        chunks: List[str] = []
        for n in retrieved.get("nodes", []):
            if n.get("label") == "Chunk":
                txt = (n.get("properties") or {}).get("text")
                if txt:
                    chunks.append(txt)
        context = "\n---\n".join(chunks[:5])
        answer = ""
        if context and gemini_client.is_configured():  # type: ignore[attr-defined]
            try:
                ans = await gemini_client.generate_study_answer(question, context)  # type: ignore
                if ans:
                    answer = ans.strip()
            except Exception:
                logger.warning("answer_llm_failed")
        dur = time.perf_counter() - t0
        self.metrics["answer_latency_sum"] += dur
        self.metrics["answer_latency_count"] += 1
        return {
            "answer": answer,
            "context_nodes": retrieved.get("nodes", []),
            "context_edges": retrieved.get("edges", []),
            "retrieval_meta": retrieved.get("meta", {}),
            "contributing_ids": [n.get("id") for n in retrieved.get("nodes", []) if n.get("id")],
        }

    # ---------------------- Shortest Path ----------------------
    async def shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        *,
        namespace: Optional[str] = None,  # reserved for future namespace scoping
    ) -> Dict[str, Any]:
        if source_id == target_id:
            return {"path": [source_id]}
        if self.graph_store == "neo4j" and self.neo4j_driver:
            try:
                async with self.neo4j_driver.session() as session:  # type: ignore
                    data = await session.execute_read(
                        lambda tx, s, t, d: tx.run(
                            "MATCH (a {id:$s}),(b {id:$t}), p = shortestPath((a)-[*..$d]-(b)) RETURN p",
                            s=s,
                            t=t,
                            d=d,
                        ).data(),
                        source_id,
                        target_id,
                        max_depth,
                    )
                    if data:
                        rec = data[0]
                        p = rec.get("p")
                        if p:
                            try:
                                node_ids = [
                                    getattr(n, "id", None)
                                    or (n.get("id") if isinstance(n, dict) else None)
                                    for n in getattr(p, "nodes", [])
                                ]
                                node_ids = [n for n in node_ids if n]
                                if node_ids:
                                    return {"path": node_ids}
                            except Exception:  # pragma: no cover
                                pass
            except Exception:
                logger.exception("neo4j_path_failed")
        # SQLite BFS fallback
        from collections import deque
        async with get_db_session() as session:
            res = await session.execute(select(GraphEdge))
            graph: Dict[str, Set[str]] = {}
            for e in res.scalars().all():
                graph.setdefault(e.source_id, set()).add(e.target_id)
                graph.setdefault(e.target_id, set()).add(e.source_id)
            prev: Dict[str, Optional[str]] = {source_id: None}
            q = deque([source_id])
            found = False
            while q:
                cur = q.popleft()
                if cur == target_id:
                    found = True
                    break
                for nb in graph.get(cur, set()):
                    if nb not in prev:
                        prev[nb] = cur
                        q.append(nb)
                        if len(prev) > 5000:
                            break
            if not found:
                return {"path": []}
            seq: List[str] = []
            node = target_id
            while node is not None:
                seq.append(node)
                node = prev.get(node)
            seq.reverse()
            return {"path": seq}

    # ---------------------- Snapshots ----------------------
    async def create_snapshot(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        ns = namespace or settings.DEFAULT_NAMESPACE
        async with get_db_session() as session:
            # counts
            nres = await session.execute(select(GraphNode.id).where((GraphNode.namespace == ns) | (GraphNode.namespace.is_(None))))
            node_ids = [r[0] for r in nres.all()]
            eres = await session.execute(select(GraphEdge.id))
            edge_ids = [r[0] for r in eres.all()]
            mod = None
            try:
                from app.services.cluster_service import cluster_service  # local import to avoid cycle
                cr = cluster_service._cache.get((ns, "louvain"))
                if cr:
                    mod = cr.modularity
            except Exception:
                pass
            snap_id = str(uuid.uuid4())
            # cluster sizes
            from app.models.database import GraphClusterMembership, GraphSnapshot
            cres = await session.execute(select(GraphClusterMembership.cluster_id).where(GraphClusterMembership.namespace == ns))
            from collections import Counter
            c_counts = Counter([r[0] for r in cres.all()])
            meta = {"cluster_sizes": dict(c_counts)}
            rec = GraphSnapshot(id=snap_id, namespace=ns, node_count=len(node_ids), edge_count=len(edge_ids), modularity=mod, metadata_json=meta)
            session.add(rec)
            await session.commit()
            self.metrics["snapshots_created"] += 1
            return {"snapshot_id": snap_id, "node_count": len(node_ids), "edge_count": len(edge_ids), "modularity": mod}

    async def list_snapshots(self, namespace: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        ns = namespace or settings.DEFAULT_NAMESPACE
        async with get_db_session() as session:
            from app.models.database import GraphSnapshot
            res = await session.execute(select(GraphSnapshot).where(GraphSnapshot.namespace == ns).order_by(GraphSnapshot.created_at.desc()).limit(limit))
            out: List[Dict[str, Any]] = []
            for s in res.scalars().all():
                out.append({
                    "id": s.id,
                    "created_at": s.created_at.isoformat() if getattr(s, 'created_at', None) else None,
                    "node_count": s.node_count,
                    "edge_count": s.edge_count,
                    "modularity": s.modularity,
                })
            return out

    async def diff_snapshots(self, snapshot_a: str, snapshot_b: str) -> Dict[str, Any]:
        async with get_db_session() as session:
            from app.models.database import GraphSnapshot
            sa = (await session.execute(select(GraphSnapshot).where(GraphSnapshot.id == snapshot_a))).scalars().first()
            sb = (await session.execute(select(GraphSnapshot).where(GraphSnapshot.id == snapshot_b))).scalars().first()
            if not sa or not sb:
                return {"error": "snapshot not found"}
            # Cluster size deltas if present
            def clusters(meta):
                if not meta:
                    return {}
                return (meta or {}).get("cluster_sizes", {})
            ca = clusters(getattr(sa, 'metadata_json', {}) or {})
            cb = clusters(getattr(sb, 'metadata_json', {}) or {})
            # Compute added/removed clusters (ids) and size changes
            cluster_changes: Dict[str, Any] = {"added": {}, "removed": {}, "size_delta": {}}
            for cid, sz in cb.items():
                if cid not in ca:
                    cluster_changes["added"][cid] = sz
                else:
                    delta = sz - ca[cid]
                    if delta:
                        cluster_changes["size_delta"][cid] = delta
            for cid, sz in ca.items():
                if cid not in cb:
                    cluster_changes["removed"][cid] = sz
            return {
                "a": sa.id,
                "b": sb.id,
                "delta_nodes": sb.node_count - sa.node_count,
                "delta_edges": sb.edge_count - sa.edge_count,
                "delta_modularity": (sb.modularity or 0) - (sa.modularity or 0),
                "clusters": cluster_changes,
            }


graphrag_service = GraphRAGService()
