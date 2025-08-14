# GraphRAG Integration Plan for Open WebUI

## Overview
This document outlines a phased, robust plan for integrating a GraphRAG system into Open WebUI. The goal is to enable automatic knowledge graph creation from ingested documents, hybrid semantic and graph-based retrieval, and future visualization support—all leveraging Open WebUI's pipeline and RAG architecture.

---

## Phase 1: Foundation & Architecture

### 1.1. Analyze Open WebUI Structure
- Confirm backend (FastAPI) supports plugin pipelines and RAG via vector DB (pgvector/Postgres).
- Identify pipeline extension points for knowledge ingestion, entity extraction, and retrieval.
- Review document storage and embedding model configuration.

### 1.2. Define GraphRAG Data Model
- Choose graph DB (Neo4j recommended; fallback to in-memory/SQLite for MVP).
- Define node schema: unique ID, type (entity), properties (name, description, source doc).
- Define edge schema: source node, target node, relation type, confidence score.
- Plan for vector embeddings per node/edge for hybrid search.

---

## Phase 2: Knowledge Ingestion & Graph Creation Pipeline

### 2.1. Document Ingestion
- Triggered by user upload or admin action.
- Pipeline receives document and metadata.

### 2.2. Entity & Relation Extraction
- Use LLM (Gemini, GPT-4, etc.) to extract entities and relationships from document text.
- Example prompt: "Extract all people, organizations, locations, and relationships from this text."
- Store extraction results as nodes and edges in graph DB.

### 2.3. Graph Construction & Indexing
- Create nodes/edges in graph DB with extracted data.
- Generate vector embeddings for each node (and optionally edge) using Open WebUI's embedding model.
- Store embeddings in vector DB for semantic search.
- Automatically link nodes with similar embeddings or overlapping properties; optionally use LLM for link suggestions.

### 2.4. Audit Trail
- Log ingestion actions, LLM calls, and graph mutations for transparency and debugging.

---

## Phase 3: Hybrid RAG Query Pipeline

### 3.1. Query Interception
- Pipeline inspects incoming chat queries.
- If query is informational ("Who is X?", "How does Y relate to Z?"), route to GraphRAG.

### 3.2. Hybrid Retrieval
- Vector Search: Retrieve top-k relevant nodes/documents from vector DB.
- Graph Traversal: Use graph DB to find related entities, paths, and relationships.
- LLM Synthesis: Combine retrieved context, summarize, and answer user query.

### 3.3. Response Formatting
- Present answer in chat, optionally with a "Show graph" button for future visualization.

---

## Implemented API Surface (Current State)

All endpoints are namespaced under `/api/smart-assistant/graphrag`:

Ingestion & Management:
- POST `/ingest` – Single document ingestion (heuristic or Gemini extraction).
- POST `/ingest-file` – Multipart upload ingestion (text files).
- POST `/ingest-batch` – Batch ingestion of up to 100 docs with aggregate stats.

Retrieval & QA:
- POST `/query` – Hybrid retrieval (embeddings cosine → name contains → fallback TF scoring) + adjacency expansion.
- POST `/answer` – Retrieval + Gemini answer synthesis over top chunks (if configured).

Graph Exploration:
- GET `/graph?sample=N` – Sample subgraph for visualization.
- GET `/stats` – Counts: nodes, edges, top relation frequencies.
- GET `/neighbors/{node_id}` – Ego-network (center node + immediate edges & neighbors).
- GET `/search?q=prefix` – Prefix search over node names (autocomplete helper).

Security:
- Optional header `x-api-key: <GRAPHRAG_API_KEY>` enforced if `GRAPHRAG_API_KEY` set in environment.

Feature Flags & Config:
- `ENABLE_GRAPHRAG` – Master flag.
- `GRAPH_STORE` – `sqlite` (default) | `neo4j` (minimal adapter active if `NEO4J_URI` provided).
- `EMBEDDING_PROVIDER` – Currently Gemini-only pathway in use. `disable_embeddings` flag allows fast structural runs.
- `force_heuristic` – Bypass LLM extraction for deterministic, local-only ingestion.

Retrieval Ranking Strategy:
1. If embeddings present: cosine similarity over in-memory sampled nodes (chunks+entities) capped at 1000.
2. Else name ILIKE contains.
3. Else fallback term-frequency scoring over chunk text (light BM25-esque approximation without IDF).

Neo4j Minimal Support:
- Driver initialized when configured; nodes/edges MERGE’d; mention links inferred via substring scanning; name-contains retrieval supported.
- Failure auto-falls back to SQLite code path (with error tag in `store`).

Entity→Chunk Linking:
- Substring match across all chunks (capped 10 links/entity for SQLite, 5 for Neo4j) with relation `MENTIONED_IN`.

Batch Ingestion Aggregates:
- Returns counts: total, succeeded, failed, cumulative nodes/edges created.

Answer Generation:
- Uses Gemini when context chunks available; returns empty string if model not configured.

Error Handling & Logging:
- Structured info logs for phases: chunking, extraction (strategy + counts), embeddings, upsert (chunks/entities/links), commit, failures.
- Retry/timeout layer on Gemini client to mitigate transient network issues.

Example ingest request:

	curl -X POST http://localhost:8081/api/smart-assistant/graphrag/ingest \
			 -H 'Content-Type: application/json' \
			 -d '{"doc_id":"demo-1","text":"OpenAI collaborates with Microsoft and Google on AI safety.","metadata":{"source":"demo"}}'

Example query request:

	curl -X POST http://localhost:8081/api/smart-assistant/graphrag/query \
			 -H 'Content-Type: application/json' \
			 -d '{"query":"OpenAI","top_k":5}'

Notes / Operational Considerations:
- Default store: SQLite (sufficient for low thousands of nodes). Switch to Neo4j for richer traversal & scaling.
- Embeddings: Gemini model (configurable via `EMBEDDING_MODEL`); can be disabled per request.
- Determinism: Use `force_heuristic` + `disable_embeddings` for repeatable test scenarios.
- Security: Set `GRAPHRAG_API_KEY` to gate ingestion & answer endpoints in shared environments.
- Performance: Current vector ranking is in-Python; for >50k nodes migrate to external vector DB (e.g., Qdrant already listed in deps) or add ANN index.

---

## Phase 4: Visualization & Extensibility

### 4.1. Graph Visualization API (In Progress)
- Basic sampling (`/graph`) & ego-neighborhood (`/neighbors/{id}`) & stats (`/stats`) implemented.
- Next: parameterized filters (by label, relation), pagination, degree-based pruning, path finding endpoint.

### 4.2. Extensibility & Security
- All logic implemented as pipelines for modularity.
- Embeddings for nodes/edges stored in vector DB for hybrid search.
- LLM calls leverage Open WebUI's model configuration.
- Respect user permissions; only ingest/expose data user is allowed to see.

---

## Phase 5: Remaining Roadmap

Short-Term Enhancements:
- Add relation/path query endpoint: `/paths?source=...&target=...&max_depth=...` (Neo4j optimized, SQLite fallback BFS).
- Introduce label/relation filters to `/query` and `/graph` endpoints.
- Cache embeddings (avoid duplicate recompute on repeated entity names).
- Add pagination to `/search` & `/neighbors`.

Medium-Term:
- External vector store integration (Qdrant) with upsert + search abstraction.
- Improved ranking: integrate proper BM25 or hybrid (sparse + dense) retrieval.
- Multi-tenant partitioning: namespace prefix or per-user graph segment.
- Auth integration with real user/session model.

Long-Term:
- Full Neo4j schema evolution (constraints, indexes on :Entity(name), :Chunk(doc_id, chunk_index)).
- Path explanation & provenance chain construction for answers.
- Visualization UI (force layout, incremental expansion, highlighting answer-supporting subgraph).
- Advanced enrichment jobs (periodic re-embedding, relation confidence recalibration, community detection, summarization nodes).

Testing & Quality Goals:
- Add mocked Gemini unit tests for extraction, embeddings, answer fallback.
- Add retrieval regression tests ensuring ranking stability across code changes.
- Stress test ingestion at scale with synthetic corpus (measure ingestion throughput & memory).

Observability:
- Add structured metrics counters (ingest_duration_ms, nodes_created, edges_created, retrieval_latency_ms).
- Optional OpenTelemetry export for tracing LLM + DB spans.

---

## Summary
This phased plan enables automatic knowledge graph creation, hybrid semantic/graph retrieval, and future visualization in Open WebUI. It leverages LLMs for extraction and linking, Open WebUI's pipeline and RAG architecture for extensibility, and is designed for transparency, modularity, and security.
