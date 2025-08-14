# GraphRAG Integration Plan

Version: 0.4
Status: Phase 1 DONE; Phase 2 Core DONE (orchestrator + selective delta + NOOP + symlink); Phase 3 Adapter LIVE (Gemini-native structured search + artifact cache + reasoning_chain); Phase 5 reuse/delta metrics surfaced
Last Updated: 2025-08-13
Owner: GraphRAG Working Group

## 1. Objectives
Integrate Microsoft GraphRAG library capabilities into the Smart Assistant knowledge graph pipeline to:
- Improve entity & relationship extraction quality and consistency.
- Introduce hierarchical communities and community reports for richer summarization + LOD.
- Enable incremental (delta) indexing for cost & latency efficiency.
- Enhance retrieval relevance (global/local search, drift reasoning) beyond current hybrid heuristic.
- Standardize data artifacts & storage abstraction for scalability.
- Maintain backward compatibility & visualization continuity during migration.

## 2. Current State Summary (Baseline)
Our existing ingestion (`graphrag_service.ingest_document`):
1. Section + chunk parsing (heuristic heading detection) -> section_map.
2. LLM extraction (single pass) + heuristic fallback + capitalized phrase fallback.
3. Classification enrichment (Technology/Organization/Role/Achievement heuristics).
4. Persistence of Chunk, Section, Entity nodes (SQLite / optional Neo4j) + embeddings per chunk & entity name.
5. Derived edges: CONTAINS, MENTIONED_IN, CO_OCCURS, HAS_ENTITY, ROLE_AT, USES_TECH.
6. Layout (hybrid or clustered) + degree metrics persisted in node.properties.
7. Centrality endpoint computing PageRank, betweenness, importance.
8. Retrieval: hybrid (Qdrant vector OR embed similarity) + name + BM25-lite fallback.
9. Answer: LLM summarization of top chunks.
10. Streaming SSE for node additions.

Limitations:
- No incremental update merging.
- Possible edge duplication noise.
- No community hierarchy nor community summaries (only temporary clustering for layout hulls).
- Minimal prompt tuning / extraction quality assurance.
- Coarse-grained embeddings only (chunk + entity name).
- Lacks structured artifact lineage & versioned data layers.

## 3. GraphRAG Capabilities (Relevant)
| Capability | Description | Benefit |
|------------|-------------|---------|
| Multi-step indexing | Text unitization, entity/relationship extraction, merging, community detection, reporting | Higher fidelity, structured outputs |
| Community reports & hierarchy | Summaries + optional parent/child | LOD summarization & UI hull labels |
| Incremental indexing | Detect & apply deltas | Lower recompute cost & faster updates |
| Prompt tuning | Systematic improvement of extraction prompts | Quality & recall precision gains |
| Query engine (global/local/DRIFT) | Enhanced reasoning & focused retrieval | Better answer grounding |
| Storage/vector/cache factories | Configurable backends (file, cosmosdb, etc.) | Scalability & flexibility |
| Artifact schemas (entities, relationships, communities, reports) | Standard field structure | Easier analytics, pruning |
| Pruning & weighting logic | Optimize graph shape and size | Less visualization clutter |

## 4. Gap Analysis
| Area | Current | Desired (GraphRAG) | Delta Action |
|------|---------|--------------------|--------------|
| Extraction quality | Single pass heuristic | Multi-stage refine + merge | Import final_entities / relationships |
| Communities | On-demand Louvain only | Stored communities + summaries | Import communities + reports |
| Incremental updates | None | Differential merge | Add delta tracker + run GraphRAG update CLI |
| Retrieval ranking | Hybrid primitive | Global/local/DRIFT modules | Proxy query endpoints |
| Summaries | None | Community reports (content/JSON) | Store cluster summaries table |
| Prompt tuning | None | Configurable tuning workflow | External tuning job -> improved artifacts |
| Edge noise | Raw co-occurrence inflation | Weighted, pruned relationships | Use GraphRAG weights; drop redundant |
| Data lineage | Implicit | Versioned outputs & periods | Add ingest_period + artifact_version fields |

## 5. Integration Strategy Overview
Phases:
1. Artifact Import (DONE) – read existing GraphRAG outputs -> local DB.
2. Batch Index Orchestration – containerized GraphRAG run (scheduled / threshold-triggered) + automated import.
3. Query Engine Augmentation – expose GraphRAG global/local/drift query pathways via unified API.
4. Custom Relationship Extensions – integrate domain-specific relationship extraction into indexing workflow.
5. Incremental Indexing & Delta Merge – change detection, selective re-index, merging into existing graph.
6. Full Adoption / Legacy Ingest Deprecation – switch default ingestion path, maintain compatibility layer.
7. (Future) Advanced Retrieval & Reranking – hybrid semantic + structural rerank, summary-in-the-loop.
8. (Future) Provenance & Audit Layer – fine-grained lineage, versioned artifacts, rollback.
9. (Future) Cost Optimization & Adaptive Scheduling – dynamic batch sizing, token budget governance.

## 6. Phase 1 Detailed Plan (Current Implementation)
Goal: Enable visualization + retrieval of GraphRAG-produced entities / relationships / communities without altering existing ingestion API.

### 6.1 New Tables / Fields (if needed)
(Existing tables already support clusters & summaries.) Additional optional table:
- `graphrag_import_state` (key, value) to track last imported artifact timestamps (KV). (Implemented as simple JSON row or properties entry.)

Reuse:
- GraphNode: add properties keys: `gr_source = 'graphrag_artifact'`, `community_id`, `community_level`, `entity_rank`.
- GraphEdge: add `weight` (properties) if present.
- GraphClusterMembership: ingest communities (cluster_id = community id, algorithm='graphrag').
- GraphClusterSummary: store report label & summary.

### 6.2 Artifact Mapping
Assuming GraphRAG output directory structure (simplified):
```
output/
  entities.parquet (or final_entities.*)
  relationships.parquet
  communities.parquet
  community_reports.parquet
```
Field Mapping:
| GraphRAG Field | Local Node/Edge Field | Notes |
|----------------|-----------------------|-------|
| entity_id | GraphNode.id | Stable ID (or prefixed with namespace) |
| name | GraphNode.name | |
| type | GraphNode.label | Fallback 'Entity' |
| description/summary | GraphNode.properties.summary | optional |
| embedding | GraphNode.embedding | if emitted |
| community_id | properties.community_id | also membership table |
| community_level | properties.community_level | LOD use |
| relationship_id | GraphEdge.id | |
| src_id/dst_id | GraphEdge.source_id/target_id | |
| relationship_type | GraphEdge.relation | map to uppercase |
| weight | GraphEdge.properties.weight | sizing/opacity |
| report_title | GraphClusterSummary.label | |
| report_summary | GraphClusterSummary.summary | |

### 6.3 Import Logic
Process order: entities -> relationships -> communities -> community_reports.
Deduplicate:
- Node upsert match by (namespace, lower(name)) OR entity_id if stable.
- Edge upsert match by (source_id, target_id, relation) prefer artifact weight.

Conflict Resolution:
- If node exists: merge new properties (non-destructive), update embedding if empty, accumulate source_ids.
- If edge exists: update confidence if artifact weight suggests higher reliability.

### 6.4 Namespace Handling
Configurable import namespace (default existing `DEFAULT_NAMESPACE`). Optionally partition by dataset key.

### 6.5 Command / Script
`scripts/import_graphrag_artifacts.py`:
Args:
- `--path /path/to/output`
- `--namespace public`
- `--format parquet|csv` (auto detect)
- `--commit-batch-size 500`

Outputs summary JSON:
```
{"nodes_imported":1234,"nodes_merged":345,"edges_imported":5678,"edges_merged":890,"communities":42,"reports":42}
```

### 6.6 Error Handling
- Skip rows missing mandatory IDs; collect counts.
- Log first N schema mismatches with suggestions.

### 6.7 Tests (Future)
- Fixture with synthetic minimal artifacts -> run importer -> assert node/edge/summary counts.

### 6.8 Visualization Wiring (After Import)
- Use `community_id` & `GraphClusterMembership` records as alternative bundling groups.
- Show community label (from GraphClusterSummary) in hull overlay (replace placeholder label logic if available).
- Add UI toggle: Cluster Mode Source: [Louvain|GraphRAG].

## 7. Phase 2 Preview
Container service wraps GraphRAG CLI: on threshold (N new docs) spawn indexing job; poll for completion; run import delta.

## 8. Backward Compatibility
- Legacy ingest remains default; GraphRAG artifacts augment graph (mixed provenance allowed).
- Flags: `ENABLE_GRAPHRAG_IMPORT`, `IMPORT_NAMESPACE_OVERRIDE`.

## 9. Metrics
Track:
- Import latency
- Nodes merged vs new ratio
- Edge duplication saved (skipped merges)
- Community coverage (% of nodes with community_id)

## 10. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Artifact schema drift | Version pin + schema validation step before import |
| ID collisions | Prefix with namespace if raw IDs conflict |
| Large batch memory | Stream Parquet in chunks (pyarrow batches) |
| Partial import mid-run | Use temp marker file; resume on rerun |
| Cost explosion (future pipeline) | Start with offline indexing; monitor token usage |

## 11. Implementation Tasks (Phase 1)
1. Add optional dependency (pandas/pyarrow) if not present.
2. Create import script.
3. Extend GraphNode/Edge upsert utility (reusing session context) inside script.
4. Add doc (this file) & README snippet referencing usage.
5. (Optional) Add CLI entrypoint `smartctl import-graphrag` as wrapper.
6. Manual test with synthetic sample.

## 12. Acceptance Criteria (Phase 1)
- Running script on sample artifacts populates DB with entities, relationships, communities & summaries.
- Existing visualization shows new nodes; hull labels use imported summaries when cluster mode active.
- No regressions in existing tests.

## 13. Next Actions (Phase 1 Wrap)
- (DONE) Import script & dependency.
- (PENDING UI) Toggle for community label source (GraphRAG vs heuristic).
- (PLANNED) Lightweight artifact validation command (schema check) before import.

---
Feedback welcome. This document will evolve with each phase.

## 14. Phase 2: Batch Index Orchestration (In Progress)
Objective: Enable automated generation of fresh GraphRAG artifacts from newly ingested raw documents (or deltas) on a schedule or event threshold.

Key Components:
- Orchestrator Script/Service: wraps GraphRAG CLI (python -m graphrag.index ... config.yml).
- Config Template: pinned prompts, embedding model, storage backend (local filesystem initially).
- Trigger Conditions:
  - Time-based (cron: nightly 02:00 UTC) OR
  - Volume-based (N new docs OR M% of nodes flagged stale) OR manual API trigger.
- Artifact Staging Directory: output/<ts>/ (temp) -> promote to output/latest/ on success.
- Health & Atomicity: write _RUNNING marker; upon success rename to _SUCCESS and symlink latest.
- Post-Run Import: invoke existing import-graphrag script with new path (namespace preserved).

Data Flow:
 raw_docs -> staging_text_units -> entity/rel extraction -> merge -> community detection -> report generation -> artifacts -> importer -> DB.

Implemented (Updated):
- Orchestration script `scripts/run_graphrag_index.py` invoking real GraphRAG when OPENAI_API_KEY present, else Gemini fallback (entity/relation heuristic) else dummy artifacts.
- Selective Gemini delta indexing (`run_gemini_index`) processes only stale documents (from `IngestLog`) when present.
- Delta short-circuit: returns status `NOOP` when no stale docs (avoids unnecessary run directory creation).
- API endpoint `/graphrag/index/run` (background task).
- Metrics: last_index_run_at, last_index_duration_s, last_index_status, last_index_entities_new, last_index_relationships_new, last_index_stale_docs, last_index_total_docs, last_index_indexed_docs.
- Retention pruning keeps last K run-* dirs.
- Concurrency guard via lock file `.graphrag_index.lock` (non-blocking; returns LOCKED unless --force).
- Atomic markers: `_RUNNING`, `_SUCCESS`, `_PARTIAL`, `_FAILED`, `_IMPORT_FAILED` in each run directory; plus `latest` symlink promotion on SUCCESS/PARTIAL.
- Partial detection: missing optional artifacts (communities or reports) -> PARTIAL; missing core (entities/relationships) -> FAILED.
- Import uses programmatic `import_artifacts` function for structured results.
- Gemini fallback path ensures pipeline usable without OpenAI key, maintaining artifact schema compatibility.
- Stale doc IDs marked indexed on successful selective run.
- Timezone-aware timestamps (ISO8601 UTC with 'Z') used for run markers and metrics.

Remaining Tasks (Phase 2 Enhancements):
1. Scheduler stub (cron or background periodic task) configurable via settings.
2. Metrics endpoint extension: expose new vs merged ratios, percent_reused (Phase 5 tie-in).
3. Streaming log tail endpoint (follow orchestrator.log) + pagination.
4. Refined status taxonomy surface (IMPORT_FAILED distinct) in API & metrics.
5. Additional tests: lock contention, partial artifact scenario, selective delta path (single stale doc), NOOP path.
6. Timezone-aware timestamps (replace utcnow deprecation) & consistent ISO8601 with 'Z'.

Usage (current skeleton):
```bash
python -m cli index-run --namespace public --dry-run
python -m cli index-run --namespace public --keep 7
```

Edge Cases:
- Partial failure (reports fail): still import entities/relationships; mark status PARTIAL.
- Concurrent run: second run waits or aborts with 409.

Acceptance Criteria:
- Manual trigger produces new artifacts and imports them (node/edge deltas visible).
- Cron or simulated scheduler triggers automatically.
- Metrics reflect success/failure.

## 15. Phase 3: Query Engine Augmentation
Objective: Leverage GraphRAG's enriched retrieval modes (global, local, drift reasoning) behind unified /graphrag/query v2 interface.

Additions:
- Wrapper module app/core/graphrag_query_adapter.py to call GraphRAG query pipeline with context size controls.
- API: /graphrag/query2 with params mode=[auto|global|local|drift], top_k, namespace.
- Fusion Strategy (auto): attempt local first; if relevance score < threshold escalate to global; optionally combine.
- Response Schema: { mode_used, nodes, passages, reasoning_chain?, cost_tokens }.

Implemented (Current):
- Adapter (`app/core/graphrag_query_adapter.py`) with modes auto/global/local/drift & heuristic selector.
- Structured search integration (basic/global/local/drift) attempted when GraphRAG lib + OPENAI key present.
- Fallback hybrid retrieval + advanced reranking (degree_norm + relation-weighted centrality + term overlap + mode-specific weighting).
- Metrics: per-mode query counts + latency accumulation.

Implemented Additions:
- Artifact caching in query adapter to avoid per-query CSV/parquet loads; metrics: artifact_cache_hits/misses and hit_rate surfaced in /graphrag/metrics.
- Gemini-native structured search path in QueryAdapter (no OpenAI dependency) combining term overlap, degree, and optional embeddings; reasoning_chain included in responses.

Remaining Tasks (Phase 3 Completion):
1. Add query cost metrics (approx token usage if LLM generation added later).
2. Tests covering structured_search happy path (using small synthetic artifacts) & fallback path.

Acceptance Criteria:
- query2 endpoint returns consistent results for all modes.
- auto mode chooses different path when local relevance low.
- Latency metrics captured per mode.

## 16. Phase 4: Custom Relationship Extensions
Objective: Inject ROLE_AT / USES_TECH domain relationships into the indexing workflow without post-hoc heuristics.

Approach:
- Provide custom operation node in GraphRAG pipeline (post entity extraction, pre-relationship pruning) reading raw sentence windows.
- Add lightweight pattern + LLM confirm step for ambiguous cases.

Tasks:
1. Author custom op (python module) registered in pipeline config.
2. Extend config template to include custom op entry.
3. Provide unit tests for extraction precision (synthetic fixtures).
4. Map outputs to standard relationship schema fields.

Acceptance Criteria:
- New relationships appear with appropriate relation types (ROLE_AT, USES_TECH) directly from artifacts.
- Reduction (>50%) in heuristic post-processing code for these relations.

## 17. Phase 5: Incremental Indexing & Delta Merge
Objective: Re-index only impacted text units & dependent entities/edges when documents change.

Mechanics:
- Maintain ingest_log table (doc_id, hash, first_seen, last_seen, last_indexed_ts, status).
- On orchestrator run with --since, compute changed_docs = {hash differs OR new}.
- Generate partial artifacts for changed docs; merge with previous baseline (GraphRAG merging stage already supports dedupe).
- Import only changed entity/edge rows (filter by updated_at >= run start OR presence in changed id set).

Implemented (Current Partial):
- ingest_log model present (tracks status=stale/indexed etc.).
- Orchestrator diff detection reading IngestLog -> stale_doc_ids.
- Selective delta indexing for stale docs; NOOP when none.
- Metrics: last_index_stale_docs, last_index_total_docs, last_index_indexed_docs.

Remaining Tasks (Phase 5 Core):
1. Extend importer with changed-only filtering (skip unchanged edges/nodes during merge).
2. Compute time_saved_estimate and surface at /graphrag/metrics/extended (delta to full-run heuristic).
3. Artifact merge logic: merge new subset artifacts into prior baseline before import (retain weights & community assignments where stable).
4. IngestLog hash update & stale propagation to dependent entities (if definition heuristic changes).
5. Tests: single-doc edit updates only affected entities/edges; percent_reused validation.

Acceptance Criteria:
- Editing a single source doc triggers import affecting only related entities/edges.
- Index duration scales with changed content size.

## 18. Phase 6: Full Adoption / Legacy Deprecation
Objective: Make GraphRAG pipeline the default ingestion path while preserving fallback for emergency.

Steps:
1. Feature flag DEFAULT_INGEST_MODE = legacy|graphrag (configurable).
2. Mark legacy endpoints deprecated (response header Warning).
3. Migration script to ensure all legacy-only properties migrated or flagged.
4. Documentation update: ingestion architecture version >=1.0.

Acceptance Criteria:
- New documents processed exclusively by GraphRAG path under flag.
- Smoke tests pass with legacy disabled.

## 19. Phase 7+: Future Enhancements (Brief)
| Phase | Theme | Highlights |
|-------|-------|-----------|
| 7 | Advanced Retrieval | Multi-hop path expansion + LLM reranking, structural penalties |
| 8 | Provenance & Audit | Versioned artifacts, per-edge lineage, diff rollbacks |
| 9 | Cost Optimization | Adaptive batching, prompt caching, selective summarization |
| 10 | UI Enhancements | Layered community navigation (level drill-down), timeline slider |
| 11 | Streaming Updates | SSE for incremental entity/edge additions from delta runs |
| 12 | Quality Feedback Loop | Human feedback weighting; auto prompt tweak suggestions |

## 20. Cross-Phase Metrics Dashboard (Planned)
Expose /graphrag/metrics/extended with:
- last_index_run_at, last_index_status
- nodes_total, edges_total, communities_total
- pct_nodes_with_summary, avg_cluster_size, gini_degree
- incremental_saved_time_s (phase 5+)
- last_index_percent_reused_nodes, last_index_percent_reused_edges (now populated)

## 21. Security & Governance Considerations
- Add API key scopes: ingest, index, query, admin.
- Rate limit query2 (mode=global) due to higher cost.
- Audit log entries for index runs & config changes.

## 22. Migration Risk Matrix (Updated)
| Phase | Primary Risk | Mitigation |
|-------|--------------|-----------|
| 2 | Orchestrator failures leave partial state | Atomic staging dir + success markers |
| 3 | Query latency regressions | Mode timeouts + fallback to legacy hybrid |
| 4 | Low precision custom relations | Confidence calibration + A/B flag |
| 5 | Merge logic duplicating entities | Hash-based identity & post-merge diff tests |
| 6 | User disruption during switch | Feature flag + staged rollout + rollback path |

## 23. Phase Status Snapshot
| Phase | Status | Notes |
|-------|--------|-------|
| 1 | DONE | Importer + CLI shipped |
| 2 | CORE DONE | Orchestrator + fallback + selective delta + NOOP + symlink; scheduler & advanced metrics pending |
| 3 | IN_PROGRESS | Adapter + rerank + partial structured search integration; caching & Gemini-native path pending |
| 4 | PENDING | Custom relation op scaffolding next |
| 5 | PARTIAL | IngestLog + selective delta + metrics; true merge + reuse stats pending |
| 6 | PENDING | Feature flag DEFAULT_INGEST_MODE added; enforcement + deprecation headers TBD |
