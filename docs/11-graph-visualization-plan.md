# Graph Visualization & Interaction Plan

Version: 0.3
Status: In Progress (Phase 2/3 Hybrid + Layout/Relation Filter Pass)
Owner: GraphRAG Working Group
Last Updated: 2025-08-10

## 1. Objectives
Create a modern, performant, and insightful interactive visualization layer for the GraphRAG knowledge graph that:
- Enables exploration (zoom/pan, search, filter, focus paths)
- Scales from dozens → tens of thousands of nodes with graceful degradation
- Surfaces structure (clusters, communities, roles, relation types)
- Provides semantic summarization at macro zoom levels (“area summaries”)
- Integrates retrieval / answering workflows (context highlighting)
- Respects namespaces (multi-tenant isolation) & access controls
- Is themable (dark/light), accessible (contrast + keyboard navigation), and testable

## 2. Target User Journeys
| Journey | Description | Success Signal |
|---------|-------------|----------------|
| Quick Overview | User loads namespace and sees clusters + counts | Overview drawn < 2s, cluster labels readable |
| Investigate Concept | User searches entity -> highlights node + neighbors + related chunks | Node centered + context panel updated |
| Follow Path | User requests shortest path between A and B -> visual diff highlight | Path edges emphasized, others dimmed |
| Answer Traceability | After an /answer call, underlying contributing chunks/entities glow | “Why” panel lists mapped nodes |
| Cluster Summarization | Zoomed out view shows region badges (topic summaries) | Summaries appear < 1.5s after stop zoom |
| Temporal Change (future) | User replays ingestion snapshots | Time scrub animates graph |

## 3. High-Level Architecture
```
Frontend
  ├─ Graph Canvas (WebGL / layered SVG overlay)
  │    ├─ Base Layout (force-sim, or cached positions)
  │    ├─ Interaction Layer (events, lasso, hover)
  │    ├─ Cluster Hulls & Summary Badges
  │    └─ Progressive Loader (skeleton + shimmer)
  ├─ Side Panels
  │    ├─ Node Inspector
  │    ├─ Path / Answer Trace
  │    └─ Filters & Legends
  ├─ Global Search + Command Palette
  └─ Metrics Mini Bar (counts, FPS, latency)

Backend (existing + extensions)
  ├─ /graphrag/graph (sample + filters) → upgrade to windowed streaming
  ├─ /graphrag/nodes (pagination + search)
  ├─ /graphrag/edges (pagination + filtering)
  ├─ /graphrag/path (shortest path)
  ├─ /graphrag/answer (context mapping)
  ├─ NEW: /graphrag/cluster (community detection snapshot)
  ├─ NEW: /graphrag/cluster/summarize (LLM-backed summaries)
  ├─ NEW: /graphrag/stream (SSE or WebSocket updates)
  └─ NEW: /graphrag/stats/advanced (degree distro, modularity, etc.)

Data Layer
  ├─ SQLite / Neo4j (optional) primary graph store
  ├─ Qdrant vector store (semantic search)
  ├─ Cache (Redis – optional) for layout & clusters
  └─ Artifact store for precomputed embeddings/layout snapshots
```

## 4. Technology Choices (Proposed)
| Layer | Option | Rationale |
|-------|--------|-----------|
| Core Graph Rendering | **Sigma.js (WebGL)** + Graphology | High performance, stable API, clustering ecosystem |
| Alternate (large graphs) | Cytoscape.js or `@cosmograph/cosmos` | Cytoscape mature; Cosmos for >100k nodes |
| Layout | ForceAtlas2 (GPU/WebWorker) + optional deterministic cached layout | Balances readability & speed |
| Cluster Hulls | D3 polygon hulls rendered as Canvas overlay | Light-weight + custom coloring |
| Animations | requestAnimationFrame + easing (d3-ease) | Smooth transitions |
| Summaries | LLM (Gemini) summarizing top n frequent terms per cluster | Leverages existing Gemini integration |
| State Mgmt | Zustand or Redux Toolkit (light) | Simplicity & predictable updates |
| Styling | Tailwind + design tokens | Already present toolchain alignment (frontend) |
| Accessibility | ARIA roles + fallback list view | Inclusive design |
| Testing | Playwright + Vitest snapshots (layout metadata) | Confidence across updates |

## 5. Visual Design Guidelines
- **Color Palette** (WCAG AA contrast):
  - Background: `#12161c` dark / `#ffffff` light
  - Primary Entity: `#5B8FF9`
  - Secondary / Chunk: `#36CBCB`
  - Relation edge default: `#8892a0` (alpha 0.55)
  - Highlight (search/path): `#F6BD16`
  - Danger / anomaly: `#F4664A`
  - Cluster Hull Fill (transparent): category hue + 18% alpha
- **Edge Weight Encoding:** opacity + thickness (confidence)
- **Node Size:** log-scaled degree (min 4px – max 28px)
- **Interaction:**
  - Hover: enlarge + glow outer ring
  - Focus: pin + emphasize neighbors; global dim others (alpha fade)
- **Zoom Levels:**
  - L3 (far): clusters only (aggregate nodes with count badge)
  - L2 (mid): representative centroids + top-K labeled entities
  - L1 (near): full nodes + edges + chunk mention arcs

## 6. Data Contracts (Draft)
### 6.1 Cluster Endpoint
`GET /api/smart-assistant/graphrag/cluster?namespace=public&algorithm=louvain`
Response:
```json
{
  "namespace": "public",
  "algorithm": "louvain",
  "generated_at": "2025-08-10T12:00:00Z",
  "stats": {"clusters": 12, "modularity": 0.71},
  "clusters": [
    {"id": "c1", "node_ids": ["n1","n7"], "size": 42, "top_terms": ["optimization","gradient"], "sample_nodes": ["Gradient Descent","SGD"], "centroid": {"x": 0.12, "y": -0.44}},
    {"id": "c2", "node_ids": ["n99"], "size": 8, "top_terms": ["inference"], "centroid": {"x": -0.55, "y": 0.31}}
  ]
}
```

### 6.2 Cluster Summaries
`POST /api/smart-assistant/graphrag/cluster/summarize`
Body:
```json
{"namespace":"public","cluster_ids":["c1","c2"],"max_tokens":120}
```
Response:
```json
{"summaries":{"c1":"This cluster centers on stochastic optimization...","c2":"Focuses on model inference concerns..."}}
```

### 6.3 Streaming Updates (SSE)
`GET /api/smart-assistant/graphrag/stream` emits events:
```json
{"event":"node_added","data":{"id":"n123","label":"Entity","name":"Backpropagation"}}
{"event":"edge_added","data":{"id":"e45","source_id":"n1","target_id":"n123","relation":"MENTIONED_IN"}}
```

### 6.4 Enhanced Graph Endpoint (Future)
Support `?mode=viewport&x=-1&y=-1&wx=2&wy=2` for windowed loading.

## 7. Phased Implementation Plan
### Phase 0 – Foundations (Already Partially There)
- Endpoints: nodes, edges, graph sampling (DONE)
- Add: cluster computation backend stub (synchronous first)
- Add: deterministic layout generation script (seeded force simulation) → store JSON artifact
- Metrics: baseline render FPS, average retrieval latency

### Phase 1 – Minimal Interactive Viewer
- Stack: React + Sigma.js scaffold
- Load sample via `/graphrag/graph` → render
- Pan/zoom, node hover, sidebar inspector
- Color & size encodings applied
- Path highlight consumption of `/graphrag/path`
- Success Criteria: < 2s first meaningful paint (500 nodes)

### Phase 2 – Progressive & Paginated Loading
- Use `/graphrag/nodes` & `/graphrag/edges` incrementally (infinite scroll style)
- Debounce search bar (300ms) hitting `/graphrag/search`
- Add loading spinner overlays + skeleton nodes
- Basic client cache & eviction (LRU by recency)

### Phase 3 – Community Detection & Summaries
- Implement server Louvain (pure Python or networkx) job (async task)
- `/cluster` endpoint returns cached clusters (TTL configurable)
- LLM summary: gather node names + top terms → gemini summarization with cost guard
- Display cluster hulls + tooltips + badges when zoom < threshold
- Success: Summaries appear < 1.5s (excluding initial compute)

### Phase 4 – Multi-Scale Rendering & Level-of-Detail (LOD)
- Zoom thresholds trigger different draw layers
- Replace nodes with aggregated cluster centroid glyphs at far zoom
- Animate transitions (easeCubic) reusing previous positions
- Pre-calc cluster centroids using layout positions

### Phase 5 – Performance & Stability
- Move layout & heavy metrics to WebWorker
- Add dynamic throttling (pause layout when idle)
- Implement FPS monitor + degrade features (e.g., edge arrows) < 30 FPS
- Add optional WebGL instanced rendering fallback (if node count > 5k)

### Phase 6 – Semantic Overlays
- Answer trace: pass `question` to `/answer` → highlight contributing chunk nodes (pulse animation)
- Add “semantic ring” around nodes with top embedding similarity to current focus
- Introduce diff mode (compare two namespaces or snapshots)

### Phase 7 – Real-Time / Streaming (Optional)
- SSE `/stream` for new ingest events → add nodes with ‘pop’ animation
- Batched re-cluster trigger after threshold (e.g., +250 nodes)

### Phase 8 – Security & Multi-Tenancy Hardening
- Enforce namespace scoping on all new endpoints
- API key gating (already partially supported) extended to cluster/stream endpoints
- Add rate limiting (Redis token bucket) for summary generation

### Phase 9 – QA, Testing & Telemetry
- Playwright visual regression of small canonical graph
- Snapshot layout & cluster JSON – diff on PR
- Instrument custom events: node_click, path_request, cluster_expand
- SLOs: 95p interactions < 120ms handler time; initial load error rate < 1%

### Phase 10 – Documentation & Developer Experience
- Add architecture diagram + how-to extend cluster algorithms
- Provide theming guide + palette tokens file
- Publish performance tuning checklist

## 8. Backend Additions (Implementation Notes)
| Feature | Change |
|---------|--------|
| Clustering | Add `cluster_service.py` (compute + cache) |
| Summaries | Add `summarize_cluster` using Gemini (rate limited) |
| Streaming | Add SSE endpoint using async generator (FastAPI `EventSourceResponse`) |
| Layout Cache | Maintain `graph_layout` table (node_id, x, y, namespace, layout_version) |
| Viewport Query | Extend `/graphrag/graph` to accept bounding box | 

## 9. Layout Strategy
1. **Seeded ForceAtlas2** (deterministic seed → stable positions) executed once per namespace after major ingest batch.
2. Cache coordinates in DB; store `layout_version` hash = (namespace + node_count + timestamp bucket).
3. On large mutation ( >10% new nodes ), schedule re-layout in background.
4. Provide `/graphrag/layout/status` to query freshness.

## 10. Cluster Computation Strategy
- Input: Induced subgraph (namespace)
- Use networkx or graphology offline script for Louvain
- Persist cluster_id mapping in `graph_cluster_membership` (node_id, cluster_id, namespace)
- Compute top terms: Aggregate chunk texts for nodes in cluster → tokenize → TF-IDF top n = 8
- Summarization prompt (Gemini): "Summarize these terms & sample entities into a concise topic label (<12 words) and a 2-sentence description".

## 11. Summarization Cost Control
| Mechanism | Detail |
|-----------|--------|
| Caching | Hash set of (cluster_id, top_terms_hash) → summary reuse |
| Budget | Daily cluster summary token allowance per namespace |
| Fallback | If LLM disabled: generate label via frequent n-grams |

## 12. Interaction Design Details
| Interaction | Behavior |
|-------------|----------|
| Hover Node | Show mini-popover (name, label, degree, cluster) |
| Click Node | Center, freeze layout, load neighbors if not present |
| Double Click | Expand 2-hop neighborhood (bounded) |
| Lasso Select | Bulk select → aggregate stats in sidebar |
| Path Mode | Select source then target → call `/path` → highlight path edges/nodes |
| Cluster Toggle | Click hull → zoom to cluster bounds + expand to full detail |
| Search | Typeahead using `/graphrag/search` (prefix) |
| Keyboard | `Ctrl+K` command palette (jump to node, run path, filter) |

## 13. Accessibility Considerations
- Minimum 4.5:1 contrast on labels
- Provide tab cycle through highlighted nodes list
- Offer non-visual JSON list view of current viewport (`Export` button)
- Animations respect `prefers-reduced-motion`

## 14. Performance Targets
| Metric | Target |
|--------|--------|
| First Paint (500 nodes) | < 2000 ms |
| Incremental fetch append | < 300 ms |
| Cluster summarization (LLM) | < 2.5 s (cold) / < 400 ms (cached) |
| Path highlight animation | < 120 ms start |
| FPS (typical) | ≥ 50 WebGL / ≥ 30 Canvas fallback |

## 15. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Large graph memory blow-up | Canvas freeze | Progressive loading + LOD pruning |
| LLM cost spikes | Budget overrun | Token budgeting + caching + manual trigger |
| Layout jitter on updates | User confusion | Freeze positions + incremental layout in worker |
| Cluster recompute latency | Stale summaries | TTL + background recompute + status endpoint |
| WebGL incompatibility | User blocked | Feature detect → fallback to SVG/Canvas |
| Multi-tenant leak | Data exposure | Namespace enforced at query layer + tests |

## 16. Success Metrics (KPIs)
- Engagement: ≥ 30% of RAG queries involve at least one graph interaction
- Retention: Repeat visualization sessions per user per week ≥ 2
- Performance: 95p answer trace overlay < 800 ms end-to-end
- Stability: < 0.5% frontend graph rendering errors (captured via telemetry)

## 17. Phase Exit Criteria Summary
| Phase | Exit Criteria |
|-------|---------------|
| 1 | Interactive viewer, inspect + path works |
| 2 | Progressive loading & search stable |
| 3 | Clusters + basic summaries visible |
| 4 | LOD transitions smooth (<150ms) |
| 5 | Worker-based layout + FPS guard |
| 6 | Answer trace + semantic ring delivered |
| 7 | Streaming ingest events integrated |
| 8 | Security tests pass (namespace isolation) |
| 9 | Visual regression + telemetry dashboards |
| 10 | Docs / theming guide published |

## 18. Immediate Next Steps (Updated)
Implemented so far (delta v0.2 → v0.3):
- Phase 1 core viewer (Sigma.js) with path highlight, search, sidebar, semantic ring.
- Progressive loading (Phase 2) via `/nodes` + on-demand `/edges` with LRU eviction.
- Section / chunk parsing + enriched edge types (CONTAINS, HAS_ENTITY, CO_OCCURS, MENTIONED_IN).
- Deterministic hybrid layout (sections radial anchors + spring refinement) persisted per node.
- Heuristic classification enrichment (Technology, Organization, Role, Achievement) + derived ROLE_AT / USES_TECH relations.
- Basic FPS monitoring & degradation toggle (edge thinning) (early Phase 5 element).
- SSE streaming for node additions (Phase 7 seed).
 - Degree + normalized degree (`degree_norm`) persisted for sizing.
 - Cluster & hybrid layout recompute endpoint `/graphrag/layout/recompute` (hybrid + clustered mode prototype).
 - Frontend: degree-based node sizing, relation filter dropdown, layout mode buttons, edge label toggle.
 - Namespace column persisted directly on nodes (future faster filtering).

Gap vs. Reference (Wikipedia-style) Visualization:
| Aspect | Current | Target | Action Plan |
|--------|---------|--------|-------------|
| Layout Cohesion | Semi-arc / dispersed; sections radial + spring | Dense radial / organic with clear hubs | Improve clustered layout spacing (cluster centers via force on meta-graph + intra-cluster FA2) |
| Community Separation | Hulls (basic) w/out repulsion | Clearly spaced colored clusters | Add cluster-level collision/spacing & alpha halos, gravity dampening between clusters |
| Node Sizing | Degree_norm scaled (basic) | Multi-metric (degree + centrality + type weighting) | Compute betweenness/PR offline; store centrality composite score |
| Edge Clarity | Straight thin lines; overlapping | Curved / bundled edges reducing clutter | Implement simple quadratic curves for cross-cluster edges; optional edge bundling pass |
| Labels | All rendered (crowding) | Priority labels (hubs) with fade-in | Dynamic label budget per frame using screen-space occupancy grid |
| Interaction | Hover, path, search, relation filter | Rich focus mode, cluster expand, lasso | Implement cluster expand + lasso selection plugin |
| Visual Hierarchy | Chunks toggle; achievements hidden far zoom | Progressive LOD tiers (aggregate glyphs) | Introduce pseudo-nodes (cluster centroids) at far zoom |
| Semantic Grouping | Section anchors only | Multi-level: sections + clusters + roles | Add ring layout layer for section-to-cluster mapping |
| Edge Semantics | Relation filter only | Color + legend + thickness by type/confidence | Map relation → color palette & encode confidence in opacity |
| Performance | FPS monitor + edge thinning | Adaptive frame budget + worker layout | Move heavy centrality & layout to worker + incremental frames |

Next incremental tasks (v0.3 → v0.4):
1. Edge labeling & filtering UI (relation type toggles, legend augmentation).
2. Gesture polish: trackpad-friendly pan (two-finger) + wheel zoom smoothing; add pinch detection.
3. Cluster service integration: persist cluster memberships; display hulls only from backend cluster data (replace placeholder logic when ready).
4. LOD tiering: implement aggregate centroid glyphs for far zoom (replace manual hiding heuristics).
5. Label density control: dynamic label culling based on screen space / degree.
6. Snapshot diff overlays (color edges/nodes added/removed between snapshots).
7. Background re-layout scheduling on >10% node growth with layout_version tracking endpoint.
8. Unit tests: ingestion classification, relation inference counts, layout coordinate presence.
9. Add `/graphrag/stats/advanced` for degree distribution & relation histogram (fuel UI filters).
10. Introduce cluster summarization prompts once cluster persistence stabilized.
 11. Centrality computation job: betweenness + PageRank persisted for multi-metric size.
 12. Curved edge renderer + relation color mapping.
 13. Label decluttering grid + fade-in animation on zoom threshold crossing.
 14. Lasso select & bulk operations panel (export, summarize selection).
 15. Edge bundling prototype (force-directed edge bundling precompute) for dense clusters.

### Delta Implemented (toward v0.4)
Added since v0.3 drafting (now completed):
- Centrality endpoint (`/graphrag/centrality/recompute`) computing PageRank + betweenness with size guards and persisting `pagerank_norm`, `betweenness_norm`, `importance` (composite with degree_norm).
- Frontend node sizing switched to `importance` metric (improves semantic hierarchy clarity).
- Label density control: Sparse/All toggle with screen-space grid culling retaining top-importance node per cell plus high-importance override.
- Inter-cluster edge bundling Phase 2: switched from synthetic bundle nodes + split edges to overlay-rendered aggregated quadratic curves (original cross-cluster edges hidden, drawn in a canvas layer with thickness & color by group size/hash).
- Baseline curved edge rendering for all edges (quadratic curvature varying by intra vs inter-cluster) via dedicated overlay canvas; keeps Sigma for nodes while decluttering overlapping straight segments.
- Centrality recompute UI button; triggers refresh and re-sizes nodes without page reload.

In Progress / Next for v0.4:
- Encode edge confidence (thickness/opacity) and relation-specific dash or curvature styles; add legend.
- Animate bundling transitions & label fade on zoom and centrality recompute.
- Cluster centroid glyph LOD (aggregate nodes at far zoom) feeding into bundling curve endpoints.

Deferred (later phases): WebWorker offload for layout, command palette, accessibility keyboard nav, full theming tokens.

---
**Appendix A – Example Summarization Prompt**
```
You are labeling graph clusters. Given:
TOP_TERMS: gradient, descent, optimization, learning rate, convergence
SAMPLE_ENTITIES: Gradient Descent, SGD, Momentum
Return JSON: {"label": "... <12 words>", "summary": "Two concise sentences."}
```

**Appendix B – Data Volume Strategy**
- < 1k nodes: Full load OK
- 1k–10k: Paging + on-demand neighbor expansion
- 10k–50k: LOD + server-side clustering mandatory
- >50k: Pre-aggregate, disable per-edge rendering at far zoom

---
Feedback welcome. On acceptance, we will create tracked issues per phase with granular tasks. 
