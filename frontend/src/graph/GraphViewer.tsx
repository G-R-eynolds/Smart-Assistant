import React, { useEffect, useState, useRef, useCallback } from 'react';
import Sigma from 'sigma';
import { MultiDirectedGraph } from 'graphology';
// (Phase 5) Optionally offload heavy tasks to a Web Worker (placeholder)
// const layoutWorker = new Worker(new URL('./layoutWorker.js', import.meta.url));

interface GraphNodeData { id: string; label: string; name: string; properties?: any; }
interface GraphEdgeData { id: string; source_id: string; target_id: string; relation: string; confidence?: number; }
interface GraphSampleResponse { nodes: GraphNodeData[]; edges: GraphEdgeData[]; namespace?: string; }

const palette = {
  background: '#12161c',
  entity: '#5B8FF9',
  technology: '#2ecc71',
  organization: '#e67e22',
  role: '#9b59b6',
  achievement: '#F6BD16',
  section: '#3498db',
  chunk: '#586e75',
  highlight: '#f1c40f',
  edge: '#8892a0'
};

const relationColors: Record<string,string> = {
  'CO_OCCURS': '#6c8ae4',
  'HAS_ENTITY': '#af68d9',
  'CONTAINS': '#ff9f43',
  'MENTIONED_IN': '#5dade2',
  'ROLE_AT': '#f39c12',
  'USES_TECH': '#2ecc71',
};

type PathResult = { path: string[]; edges: { id: string; source_id: string; target_id: string }[] } | null;

interface GraphViewerProps { namespace?: string }
export const GraphViewer: React.FC<GraphViewerProps> = ({ namespace }: GraphViewerProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const hullCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const curveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const graphRef = useRef(new MultiDirectedGraph());
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [semanticRingIds, setSemanticRingIds] = useState<Set<string>>(new Set());
  const [answerOverlayIds, setAnswerOverlayIds] = useState<Set<string>>(new Set());
  const fpsRef = useRef<HTMLDivElement | null>(null);
  const lastFrame = useRef(performance.now());
  const frameCount = useRef(0);
  const [fps, setFps] = useState<number>(0);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [secondNode, setSecondNode] = useState<string | null>(null);
  const [pathMode, setPathMode] = useState(false);
  const [pathResult, setPathResult] = useState<PathResult>(null);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [activeNamespace, setActiveNamespace] = useState<string | undefined>(namespace);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{id:string; name:string; label:string}[]>([]);
  // Phase 3 cluster state
  const [clusters, setClusters] = useState<any[]>([]);
  const [clusterSummaries, setClusterSummaries] = useState<Record<string, {label:string; summary:string}>>({});
  const [clustersLoading, setClustersLoading] = useState(false);
  // Snapshots (Phase 11+)
  const [snapshots, setSnapshots] = useState<{id:string; created_at?:string; node_count:number; edge_count:number; modularity?:number}[]>([]);
  const [snapshotDiff, setSnapshotDiff] = useState<any | null>(null);
  const [creatingSnapshot, setCreatingSnapshot] = useState(false);
  // Provenance
  const [provenance, setProvenance] = useState<any | null>(null);
  const [showProvenance, setShowProvenance] = useState(false);
  // Live stream status
  const [streamConnected, setStreamConnected] = useState(false);
  const searchTimeout = useRef<number | null>(null);
  // Progressive loading state (Phase 2)
  const [nodesCursor, setNodesCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const MAX_NODES = 800; // LRU eviction threshold
  const nodeAges = useRef<Map<string, number>>(new Map());
  const [showChunks, setShowChunks] = useState(false);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [relationFilter, setRelationFilter] = useState<string>('*');
  const [availableRelations, setAvailableRelations] = useState<string[]>([]);
  const [labelDensity, setLabelDensity] = useState<'auto'|'all'>('auto');
  const [bundling, setBundling] = useState(false);
  const [confidenceWeighting, setConfidenceWeighting] = useState(true);
  const bundleStateRef = useRef<{active:boolean; createdNodes:Set<string>; hiddenEdges:Set<string>}>({active:false, createdNodes:new Set(), hiddenEdges:new Set()});
  const nodeClusterMapRef = useRef<Map<string,string>>(new Map());

  // Performance timing
  const firstPaintLogged = useRef(false);

  const colorReset = () => {
    const g = graphRef.current;
  g.forEachNode((node: any, attrs: any) => {
      const raw: any = attrs.raw;
      g.setNodeAttribute(node, 'color', raw?.label === 'Chunk' ? palette.chunk : palette.entity);
      g.setNodeAttribute(node, 'zIndex', 0);
      g.setNodeAttribute(node, 'hidden', false);
    });
  g.forEachEdge((edge: any, attrs: any) => {
      g.setEdgeAttribute(edge, 'color', palette.edge);
      g.setEdgeAttribute(edge, 'size', 1);
      g.setEdgeAttribute(edge, 'hidden', false);
    });
  };

  const fetchNamespaces = useCallback(async () => {
    try {
      const res = await fetch('/api/smart-assistant/graphrag/namespaces');
      if (res.ok) {
        const data = await res.json();
        setNamespaces(data.namespaces || []);
      }
    } catch (e) {}
  }, []);

  const fetchSample = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const ns = activeNamespace || namespace;
      const qs = ns ? `?namespace=${encodeURIComponent(ns)}` : '';
      const res = await fetch(`/api/smart-assistant/graphrag/graph${qs}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: GraphSampleResponse = await res.json();
      const g = graphRef.current;
      g.clear();
      const rels = new Set<string>();
      data.edges.forEach(e => rels.add(e.relation));
      setAvailableRelations(Array.from(rels));
      data.nodes.forEach((n, i) => {
        const lbl = (n.label||'Entity').toLowerCase();
        const baseColor = lbl === 'technology'? palette.technology : lbl === 'organization'? palette.organization : lbl === 'role'? palette.role : lbl === 'achievement'? palette.achievement : lbl === 'section'? palette.section : lbl === 'chunk'? palette.chunk : palette.entity;
        const layout = (n.properties && n.properties.layout) || {};
        const px = typeof layout.x === 'number' ? layout.x : Math.cos((i / data.nodes.length) * Math.PI * 2);
        const py = typeof layout.y === 'number' ? layout.y : Math.sin((i / data.nodes.length) * Math.PI * 2);
        const degreeNorm = n.properties?.degree_norm ?? 0;
        const importance = n.properties?.importance ?? degreeNorm;
        g.addNode(n.id, {
          label: n.name,
          size: lbl === 'chunk'? 2 + importance*2 : 4 + importance*8 + (lbl === 'achievement'? 1.2:0),
          color: baseColor,
          x: px,
            y: py,
          raw: n,
          hidden: lbl === 'chunk' && !showChunks
        });
      });
      data.edges.forEach(e => {
        if (g.hasNode(e.source_id) && g.hasNode(e.target_id)) {
          if (relationFilter !== '*' && e.relation !== relationFilter) return;
          const conf = typeof (e as any).confidence === 'number' ? (e as any).confidence : 0.6;
          g.addEdgeWithKey(e.id, e.source_id, e.target_id, {
            label: e.relation,
            color: relationColors[e.relation] || palette.edge,
            size: confidenceWeighting ? 0.4 + conf * 1.6 : 1,
            confidence: conf
          });
        }
      });
      if (!sigmaRef.current && containerRef.current) {
        sigmaRef.current = new Sigma(g, containerRef.current, {
          renderLabels: true,
          enableEdgeEvents: true
        });
  // Track zoom for LOD switching
  sigmaRef.current.getCamera().on('updated', () => {
          const r = sigmaRef.current!.getCamera().getState().ratio;
          setZoomLevel(r);
        });
  sigmaRef.current.on('clickNode', ({ node }: any) => {
          if (pathMode) {
            if (!selectedNode) {
              setSelectedNode(node);
              setSecondNode(null);
            } else if (selectedNode && node !== selectedNode) {
              setSecondNode(node);
            }
          } else {
            setSelectedNode(node);
            setSecondNode(null);
            setPathResult(null);
          }
        });
  sigmaRef.current.on('enterNode', ({ node }: any) => {
          const g2 = graphRef.current;
            const neighbors = new Set<string>();
            g2.forEachNeighbor(node, (n: any) => neighbors.add(n));
            g2.forEachNode((n: any) => {
              g2.setNodeAttribute(n, 'color', neighbors.has(n) || n === node ? g2.getNodeAttribute(n, 'color') : '#333');
              g2.setNodeAttribute(n, 'zIndex', neighbors.has(n) || n === node ? 1 : 0);
            });
        });
        sigmaRef.current.on('leaveNode', () => {
          colorReset();
          highlightPath(pathResult);
        });
      } else {
        sigmaRef.current?.refresh();
      }
      if (!firstPaintLogged.current) {
        firstPaintLogged.current = true;
        console.log('[GraphViewer] First paint at', performance.now());
      }
    } catch (e: any) {
      setError(e.message || 'Failed loading graph');
    } finally {
      setLoading(false);
    }
  }, [namespace, activeNamespace, pathMode, selectedNode, pathResult]);

  // Progressive node loading using /graphrag/nodes (initial + pagination)
  const loadNodesPage = useCallback(async (reset: boolean = false) => {
    if (loadingMore && !reset) return;
    try {
      if (reset) {
        setNodesCursor(null);
        setHasMore(true);
        nodeAges.current.clear();
        graphRef.current.clear();
        sigmaRef.current?.refresh();
      }
      if (!hasMore && !reset) return;
      setLoadingMore(true);
      const params = new URLSearchParams();
      if (activeNamespace) params.set('namespace', activeNamespace);
      params.set('limit', '150');
      if (nodesCursor) params.set('cursor', nodesCursor);
      const res = await fetch(`/api/smart-assistant/graphrag/nodes?${params.toString()}`);
      if (!res.ok) throw new Error('nodes fetch failed');
      const data = await res.json();
      const g = graphRef.current;
      const now = Date.now();
      const newIds: string[] = [];
      (data.results || []).forEach((n: any, i: number) => {
        if (!g.hasNode(n.id)) {
          const lbl = (n.label||'Entity').toLowerCase();
          const baseColor = lbl === 'technology'? palette.technology : lbl === 'organization'? palette.organization : lbl === 'role'? palette.role : lbl === 'achievement'? palette.achievement : lbl === 'section'? palette.section : lbl === 'chunk'? palette.chunk : palette.entity;
          const layout = (n.properties && n.properties.layout) || {};
          const px = typeof layout.x === 'number' ? layout.x : Math.cos((g.order + i) / 50) * 1.0 + Math.random() * 0.01;
          const py = typeof layout.y === 'number' ? layout.y : Math.sin((g.order + i) / 50) * 1.0 + Math.random() * 0.01;
          const degreeNorm = n.properties?.degree_norm ?? 0;
          const importance = n.properties?.importance ?? degreeNorm;
          g.addNode(n.id, {
            label: n.name,
            size: lbl === 'chunk'? 2 + importance*2 : 4 + importance*8 + (lbl === 'achievement'? 1.2:0),
            color: baseColor,
            x: px,
              y: py,
            raw: n,
            hidden: lbl === 'chunk' && !showChunks
          });
        }
        nodeAges.current.set(n.id, now);
        newIds.push(n.id);
      });
      // If this is the first batch and we have no renderer yet, create Sigma now.
      if (!sigmaRef.current && containerRef.current) {
        sigmaRef.current = new Sigma(g, containerRef.current, { renderLabels: true, enableEdgeEvents: true });
        sigmaRef.current.getCamera().on('updated', () => {
          const r = sigmaRef.current!.getCamera().getState().ratio;
          setZoomLevel(r);
        });
        sigmaRef.current.on('clickNode', ({ node }: any) => {
          if (pathMode) {
            if (!selectedNode) {
              setSelectedNode(node);
              setSecondNode(null);
            } else if (selectedNode && node !== selectedNode) {
              setSecondNode(node);
            }
          } else {
            setSelectedNode(node);
            setSecondNode(null);
            setPathResult(null);
          }
        });
        sigmaRef.current.on('enterNode', ({ node }: any) => {
          const g2 = graphRef.current;
          const neighbors = new Set<string>();
          g2.forEachNeighbor(node, (n: any) => neighbors.add(n));
          g2.forEachNode((n: any) => {
            g2.setNodeAttribute(n, 'color', neighbors.has(n) || n === node ? g2.getNodeAttribute(n, 'color') : '#333');
            g2.setNodeAttribute(n, 'zIndex', neighbors.has(n) || n === node ? 1 : 0);
          });
        });
        sigmaRef.current.on('leaveNode', () => {
          colorReset();
          highlightPath(pathResult);
        });
      }
      setNodesCursor(data.cursor || null);
      setHasMore(Boolean(data.cursor));
      // Fetch edges related to new nodes for context (bounded)
      if (newIds.length) {
        const edgeParams = new URLSearchParams();
        if (activeNamespace) edgeParams.set('namespace', activeNamespace);
        edgeParams.set('node_ids', newIds.slice(0, 100).join(','));
        edgeParams.set('limit', '400');
        const er = await fetch(`/api/smart-assistant/graphrag/edges?${edgeParams.toString()}`);
        if (er.ok) {
          const edata = await er.json();
    (edata.results || []).forEach((e: any) => {
              if (g.hasNode(e.source_id) && g.hasNode(e.target_id) && !g.hasEdge(e.id)) {
                if (relationFilter === '*' || e.relation === relationFilter) {
      const conf = typeof e.confidence === 'number' ? e.confidence : 0.6;
      try { g.addEdgeWithKey(e.id, e.source_id, e.target_id, { label: e.relation, color: relationColors[e.relation] || palette.edge, size: confidenceWeighting ? 0.4 + conf * 1.6 : 1, confidence: conf }); } catch {}
                }
              }
            });
        }
      }
      // LRU eviction
      if (g.order > MAX_NODES) {
        const protectedSet = new Set<string>();
        if (selectedNode) protectedSet.add(selectedNode);
        if (pathResult) (pathResult.path || []).forEach(id => protectedSet.add(id));
        const entries = Array.from(nodeAges.current.entries()).filter(([id]) => !protectedSet.has(id));
        entries.sort((a,b) => a[1] - b[1]);
        const toRemove = entries.slice(0, Math.max(0, g.order - MAX_NODES)).map(e => e[0]);
        toRemove.forEach(id => {
          if (g.hasNode(id)) { g.dropNode(id); nodeAges.current.delete(id); }
        });
      }
      sigmaRef.current?.refresh();
      if (!firstPaintLogged.current) {
        firstPaintLogged.current = true;
        console.log('[GraphViewer] First paint (progressive) at', performance.now());
      }
    } catch (e:any) {
      setError(e.message || 'Progressive load failed');
    } finally {
      setLoadingMore(false);
    }
  }, [activeNamespace, nodesCursor, hasMore, loadingMore, selectedNode, pathResult]);

  // Viewport sampling (fetch nodes within current camera center box)
  const fetchViewport = useCallback(async () => {
    if (!sigmaRef.current) return;
    const cam = sigmaRef.current.getCamera();
    const { x, y, ratio } = cam.getState();
    // Window size scaled by zoom ratio (simple heuristic)
    const windowSpan = 2.5 * ratio; // bigger number = fewer nodes per fetch as you zoom in
    try {
      const params = new URLSearchParams();
      params.set('mode', 'viewport');
      params.set('x', x.toFixed(4));
      params.set('y', y.toFixed(4));
      params.set('wx', windowSpan.toFixed(4));
      params.set('wy', windowSpan.toFixed(4));
      params.set('sample', '180');
      if (activeNamespace) params.set('namespace', activeNamespace);
      const res = await fetch(`/api/smart-assistant/graphrag/graph?${params.toString()}`);
      if (!res.ok) return;
      const data = await res.json();
      const g = graphRef.current;
      const now = Date.now();
      (data.nodes || []).forEach((n: any) => {
        if (!g.hasNode(n.id)) {
          g.addNode(n.id, {
            label: n.name,
            size: 4 + (n.label === 'Chunk' ? 2 : 6),
            color: n.label === 'Chunk' ? palette.chunk : palette.entity,
            x: (n.properties?.layout?.x) ?? (Math.random() - 0.5),
            y: (n.properties?.layout?.y) ?? (Math.random() - 0.5),
            raw: n
          });
        }
        nodeAges.current.set(n.id, now);
      });
    (data.edges || []).forEach((e: any) => {
        if (g.hasNode(e.source_id) && g.hasNode(e.target_id) && !g.hasEdge(e.id)) {
      const conf = typeof e.confidence === 'number' ? e.confidence : 0.6;
      try { g.addEdgeWithKey(e.id, e.source_id, e.target_id, { label: e.relation, color: relationColors[e.relation] || palette.edge, size: confidenceWeighting ? 0.4 + conf * 1.6 : 1, confidence: conf }); } catch {}
        }
      });
      sigmaRef.current?.refresh();
    } catch {}
  }, [activeNamespace]);

  // Attach camera event listener for viewport loading (debounced)
  useEffect(() => {
    if (!sigmaRef.current) return;
    let t: any;
    const handler = () => {
      if (t) cancelAnimationFrame(t);
      t = requestAnimationFrame(() => { fetchViewport(); });
    };
    sigmaRef.current.getCamera().on('updated', handler);
    return () => { sigmaRef.current?.getCamera().off('updated', handler); };
  }, [fetchViewport]);

  const runSearch = useCallback(async (q: string) => {
    if (!q) { setSearchResults([]); return; }
    try {
      const res = await fetch(`/api/smart-assistant/graphrag/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (e) {}
  }, []);

  const highlightSearchResults = useCallback(() => {
    const g = graphRef.current;
  const ids = new Set(searchResults.map((r: any) => r.id));
  g.forEachNode((n: any) => {
      const base = g.getNodeAttribute(n, 'raw')?.label === 'Chunk' ? palette.chunk : palette.entity;
      g.setNodeAttribute(n, 'color', ids.size ? (ids.has(n) ? palette.highlight : '#333') : base);
    });
    sigmaRef.current?.refresh();
  }, [searchResults]);

  const highlightPath = useCallback((p: PathResult) => {
    const g = graphRef.current;
    colorReset();
    if (!p) { sigmaRef.current?.refresh(); return; }
    const pathSet = new Set(p.path);
  g.forEachNode((n: any) => {
      if (pathSet.has(n)) {
        g.setNodeAttribute(n, 'color', palette.highlight);
        g.setNodeAttribute(n, 'zIndex', 2);
      } else {
        g.setNodeAttribute(n, 'color', '#333');
      }
    });
    const edgeSet = new Set(p.edges.map(e => e.id));
  g.forEachEdge((e: any) => {
      g.setEdgeAttribute(e, 'color', edgeSet.has(e) ? palette.highlight : '#222');
      g.setEdgeAttribute(e, 'size', edgeSet.has(e) ? 2 : 1);
    });
    sigmaRef.current?.refresh();
  }, []);

  // Semantic ring highlight: thin halo for similar nodes
  const applySemanticRing = useCallback(() => {
    if (!semanticRingIds.size) return;
    const g = graphRef.current;
    g.forEachNode((n:any) => {
      if (semanticRingIds.has(n)) {
        g.setNodeAttribute(n, 'size', (g.getNodeAttribute(n,'size')||6) + 2);
      }
    });
    sigmaRef.current?.refresh();
  }, [semanticRingIds]);
  useEffect(() => { applySemanticRing(); }, [applySemanticRing]);

  const fetchSimilar = useCallback(async (nodeId: string) => {
    try {
      const params = new URLSearchParams();
      params.set('node_id', nodeId);
      const res = await fetch(`/api/smart-assistant/graphrag/similar?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setSemanticRingIds(new Set((data.similar||[]).map((s:any)=>s.id)));
      }
    } catch {}
  }, []);

  // Answer overlay: fetch answer and highlight contributing nodes
  const runAnswer = useCallback(async (question: string) => {
    try {
      const res = await fetch('/api/smart-assistant/graphrag/answer', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ question, namespace: activeNamespace, top_k: 8 }) });
      if (res.ok) {
        const data = await res.json();
        const ids = new Set<string>((data.contributing_node_ids||[]) as string[]);
        setAnswerOverlayIds(ids);
        // Visual marking
        const g = graphRef.current;
        g.forEachNode((n:any) => {
          if (ids.has(n)) g.setNodeAttribute(n, 'color', palette.highlight);
        });
        sigmaRef.current?.refresh();
      }
    } catch {}
  }, [activeNamespace]);

  // FPS monitor & degradation
  useEffect(() => {
    let running = true;
    const loop = () => {
      if (!running) return;
      const now = performance.now();
      frameCount.current++;
      if (now - lastFrame.current >= 1000) {
        setFps(frameCount.current);
        frameCount.current = 0;
        lastFrame.current = now;
      }
      if (fps < 25 && !degraded) {
        // Degrade: hide edge labels / thin edges
        const g = graphRef.current;
        g.forEachEdge((e:any) => { g.setEdgeAttribute(e, 'size', 0.5); });
        setDegraded(true);
        sigmaRef.current?.refresh();
      } else if (fps > 40 && degraded) {
        const g = graphRef.current;
        g.forEachEdge((e:any) => { g.setEdgeAttribute(e, 'size', 1); });
        setDegraded(false);
        sigmaRef.current?.refresh();
      }
      requestAnimationFrame(loop);
    };
    const id = requestAnimationFrame(loop);
    return () => { running = false; cancelAnimationFrame(id); };
  }, [fps, degraded]);

  // LOD aggregation pass (simple: fade non-centroid nodes at far zoom)
  useEffect(() => {
    const g = graphRef.current;
    const far = zoomLevel < 0.9;
    g.forEachNode((n:any) => {
      const raw = g.getNodeAttribute(n,'raw');
      if (raw?.label === 'Chunk' && !showChunks) {
        g.setNodeAttribute(n, 'hidden', true);
      } else if (raw?.label === 'Chunk' && showChunks) {
        g.setNodeAttribute(n, 'hidden', false);
      } else if (far && (raw?.label === 'Achievement')) {
        g.setNodeAttribute(n,'hidden', true);
      } else if (!far && raw?.label === 'Achievement') {
        g.setNodeAttribute(n,'hidden', false);
      }
    });
    sigmaRef.current?.refresh();
  }, [zoomLevel, showChunks]);

  // Label density culling (grid heuristic): when labelDensity==='auto', hide labels in crowded cells except highest importance.
  useEffect(() => {
    if (!sigmaRef.current) return;
    const g = graphRef.current;
    // Reset label visibility
    g.forEachNode((n:any) => { g.setNodeAttribute(n, 'labelHidden', false); });
    if (labelDensity === 'all') { sigmaRef.current.refresh(); return; }
    const cam = sigmaRef.current.getCamera();
    const { ratio } = cam.getState();
    const cellSize = 150 * ratio; // dynamic cell size scaling with zoom
    const container = sigmaRef.current.getContainer().getBoundingClientRect();
    const cells: Record<string, {id:string; importance:number; count:number}> = {};
    g.forEachNode((n:any) => {
      const x = g.getNodeAttribute(n,'x');
      const y = g.getNodeAttribute(n,'y');
      // project to screen using sigma API
      const pos = sigmaRef.current!.graphToViewport({x,y});
      const cx = Math.floor(pos.x / cellSize);
      const cy = Math.floor(pos.y / cellSize);
      const key = cx+':'+cy;
      const imp = g.getNodeAttribute(n,'raw')?.properties?.importance ?? g.getNodeAttribute(n,'raw')?.properties?.degree_norm ?? 0;
      const slot = cells[key];
      if (!slot) cells[key] = { id: n, importance: imp, count: 1 };
      else { slot.count++; if (imp > slot.importance) { slot.id = n; slot.importance = imp; } }
    });
    // Hide labels for non-top nodes in each cell if crowded >2
    const keep = new Set<string>(Object.values(cells).map(c => c.id));
    g.forEachNode((n:any) => {
      const rawImp = g.getNodeAttribute(n,'raw')?.properties?.importance;
      // Always keep very important nodes
      if (keep.has(n) || (rawImp !== undefined && rawImp > 0.85)) return;
      g.setNodeAttribute(n,'labelHidden', true);
    });
    sigmaRef.current.refresh();
  }, [labelDensity, zoomLevel, nodesCursor]);

  // Cluster hull rendering (simple convex hull via Monotonic Chain) at low zoom levels
  useEffect(() => {
    if (!sigmaRef.current || !hullCanvasRef.current) return;
    const camera = sigmaRef.current.getCamera();
    const canvas = hullCanvasRef.current;
    const context = canvas.getContext('2d');
    if (!context) return;
    const resize = () => {
      canvas.width = canvas.clientWidth * window.devicePixelRatio;
      canvas.height = canvas.clientHeight * window.devicePixelRatio;
    };
    resize();
    const project = (x:number,y:number) => sigmaRef.current!.viewportToFramedGraph({x,y}); // not needed now
    const toScreen = (graphX:number, graphY:number) => {
      // Sigma v2 provides renderer method to convert graph -> viewport via camera
      const sigma = sigmaRef.current;
      if (!sigma) return { x: 0, y: 0 };
      const cam = sigma.getCamera();
      // Manual projection (same math as sigma's internal):
      const state: any = cam.getState();
      const ratio = state.ratio;
      const angle = state.angle;
      const cos = Math.cos(angle), sin = Math.sin(angle);
      const x = (graphX * cos - graphY * sin) / ratio + state.x;
      const y = (graphX * sin + graphY * cos) / ratio + state.y;
      // Convert to pixels relative to container center
      const size = sigma.getContainer().getBoundingClientRect();
      return {
        x: (x + 1) * size.width / 2 * window.devicePixelRatio,
        y: (y + 1) * size.height / 2 * window.devicePixelRatio,
      };
    };
    function hull(points: {x:number;y:number}[]) {
      if (points.length <= 3) return points;
      const pts = points.slice().sort((a,b)=> a.x===b.x ? a.y-b.y : a.x-b.x);
      const cross = (o:any,a:any,b:any)=> (a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x);
      const lower:any[]=[]; for (const p of pts){ while (lower.length>=2 && cross(lower[lower.length-2], lower[lower.length-1], p)<=0) lower.pop(); lower.push(p);} 
      const upper:any[]=[]; for (let i=pts.length-1;i>=0;i--){ const p=pts[i]; while (upper.length>=2 && cross(upper[upper.length-2], upper[upper.length-1], p)<=0) upper.pop(); upper.push(p);} 
      upper.pop(); lower.pop(); return lower.concat(upper);
    }
    const render = () => {
      resize();
      context.clearRect(0,0,canvas.width, canvas.height);
      const zoomRatio = camera.getState().ratio;
      // Only show hulls when sufficiently zoomed out
      if (zoomRatio > 1.8) return;
      const g = graphRef.current;
      clusters.forEach((c,i) => {
        const pts: {x:number;y:number}[] = [];
        (c.node_ids||[]).forEach((nid:string) => {
          if (g.hasNode(nid)) {
            const nx = g.getNodeAttribute(nid,'x');
            const ny = g.getNodeAttribute(nid,'y');
            const scr = toScreen(nx, ny);
            pts.push({x: scr.x * window.devicePixelRatio, y: scr.y * window.devicePixelRatio});
          }
        });
        if (pts.length < 3) return;
        const poly = hull(pts);
        if (poly.length < 3) return;
        const hue = (i*57)%360;
        context.beginPath();
        context.moveTo(poly[0].x, poly[0].y);
        for (let k=1;k<poly.length;k++) context.lineTo(poly[k].x, poly[k].y);
        context.closePath();
        context.fillStyle = `hsla(${hue},65%,45%,0.18)`;
        context.strokeStyle = `hsla(${hue},65%,55%,0.55)`;
        context.lineWidth = 2;
        context.fill();
        context.stroke();
        // Label
        const label = clusterSummaries[c.id]?.label || c.id;
        context.font = `${12 * window.devicePixelRatio}px sans-serif`;
        context.fillStyle = 'rgba(255,255,255,0.85)';
        // centroid
        const cx = poly.reduce((s,p)=>s+p.x,0)/poly.length;
        const cy = poly.reduce((s,p)=>s+p.y,0)/poly.length;
        context.fillText(label, cx+4, cy-4);
      });
    };
    render();
    const onCam = () => { render(); };
    camera.on('updated', onCam);
    const interval = setInterval(render, 1500); // periodic refresh as nodes load
    window.addEventListener('resize', render);
    return () => { camera.off('updated', onCam); clearInterval(interval); window.removeEventListener('resize', render); };
  }, [clusters, clusterSummaries]);

  // Fetch shortest path when second node set
  useEffect(() => {
    const getPath = async () => {
      if (selectedNode && secondNode && selectedNode !== secondNode) {
        try {
          const res = await fetch('/api/smart-assistant/graphrag/path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_id: selectedNode, target_id: secondNode, max_depth: 6, namespace: activeNamespace })
          });
          if (res.ok) {
            const data = await res.json();
            setPathResult({ path: data.path || [], edges: data.edges || [] });
          }
        } catch (e) {}
      } else {
        setPathResult(null);
      }
    };
    getPath();
  }, [selectedNode, secondNode, activeNamespace]);

  // Apply path highlight effect
  useEffect(() => { highlightPath(pathResult); }, [pathResult, highlightPath]);

  useEffect(() => { fetchNamespaces(); }, [fetchNamespaces]);
  // Fetch clusters (Phase 3)
  const fetchClusters = useCallback(async (ns?: string) => {
    setClustersLoading(true);
    try {
      const params = new URLSearchParams();
      if (ns) params.set('namespace', ns);
      const qs = params.toString();
      const res = await fetch(`/api/smart-assistant/graphrag/cluster?${qs}`);
      if (res.ok) {
        const data = await res.json();
        setClusters(data.clusters || []);
        // Build node->cluster map for bundling
        const m = new Map<string,string>();
        (data.clusters||[]).forEach((c:any) => (c.node_ids||[]).forEach((nid:string)=> m.set(nid, c.id)));
        nodeClusterMapRef.current = m;
        // Fetch GraphRAG cluster summaries (if any)
        try {
          const sumRes = await fetch(`/api/smart-assistant/graphrag/cluster/summaries?${qs}`);
          if (sumRes.ok) {
            const sumData = await sumRes.json();
            const map: Record<string,{label:string; summary:string}> = {};
            (sumData.summaries || []).forEach((s: any) => { map[s.cluster_id] = {label: s.label || s.cluster_id, summary: s.summary || ''}; });
            setClusterSummaries(map);
          }
        } catch (_) {}
      }
    } catch (e) { /* ignore */ }
    finally { setClustersLoading(false); }
  }, []);
  useEffect(() => { fetchClusters(activeNamespace); }, [activeNamespace, fetchClusters]);

  // Centrality recompute wiring
  const recomputeCentrality = useCallback(async () => {
    try {
      await fetch('/api/smart-assistant/graphrag/centrality/recompute', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ namespace: activeNamespace }) });
      // Reload nodes to pick up importance
      await loadNodesPage(true);
    } catch {}
  }, [activeNamespace, loadNodesPage]);

  // Edge bundling logic (polyline via hidden bundle node). Called whenever bundling toggled or after reload.
  const applyBundling = useCallback(() => {
    const g = graphRef.current;
    const state = bundleStateRef.current;
    // Unhide any previously hidden edges
    if (state.active) {
      state.hiddenEdges.forEach(eid => { if (g.hasEdge(eid)) g.setEdgeAttribute(eid,'hidden', false); });
      state.hiddenEdges.clear();
      state.createdNodes.clear();
      state.active = false;
      // Remove previous group metadata
      (state as any).groups = undefined;
    }
    if (!bundling) { sigmaRef.current?.refresh(); return; }
    interface BundleGroup { key:string; cidA:string; cidB:string; edges:string[]; count:number; relations: Record<string, number>; avgConf: number };
    const groupsMap = new Map<string, BundleGroup>();
    g.forEachEdge((e:any, attrs:any, s:any, t:any) => {
      const cs = nodeClusterMapRef.current.get(s);
      const ct = nodeClusterMapRef.current.get(t);
      if (!cs || !ct || cs === ct) return;
      const key = cs < ct ? cs+'::'+ct : ct+'::'+cs;
      let grp = groupsMap.get(key);
      if (!grp) { grp = { key, cidA: cs < ct? cs: ct, cidB: cs < ct? ct: cs, edges:[], count:0, relations:{}, avgConf:0 }; groupsMap.set(key, grp); }
      grp.edges.push(e); grp.count++;
      const rel = g.getEdgeAttribute(e,'label') || g.getEdgeAttribute(e,'relation') || 'REL';
      grp.relations[rel] = (grp.relations[rel]||0)+1;
      const conf = g.getEdgeAttribute(e,'confidence') || 0.6;
      grp.avgConf += (conf - grp.avgConf)/grp.count; // incremental average
      // hide original edge for overlay drawing
      g.setEdgeAttribute(e,'hidden', true); state.hiddenEdges.add(e);
    });
    (state as any).groups = groupsMap;
    state.active = true;
    sigmaRef.current?.refresh();
  }, [bundling]);

  // Reapply bundling after loads or toggle
  useEffect(() => { applyBundling(); }, [applyBundling, nodesCursor]);

  // Curved edge & bundled overlay rendering
  useEffect(() => {
    if (!sigmaRef.current) return;
    if (!curveCanvasRef.current) return;
    const canvas = curveCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const resize = () => {
      canvas.width = canvas.clientWidth * window.devicePixelRatio;
      canvas.height = canvas.clientHeight * window.devicePixelRatio;
    };
    resize();

    const hashHue = (s:string) => {
      let h = 0; for (let i=0;i<s.length;i++) h = (h*31 + s.charCodeAt(i))>>>0; return h % 360;
    };
    const draw = () => {
      resize();
      ctx.clearRect(0,0,canvas.width, canvas.height);
      const sigmaInst = sigmaRef.current!;
      const g = graphRef.current;
      const cam = sigmaInst.getCamera();
      const state = bundleStateRef.current as any;
      // Build cluster centroids for bundling & curvature decisions
      const centroids: Record<string,{x:number;y:number;count:number}> = {};
      g.forEachNode((n:any) => {
        const cid = nodeClusterMapRef.current.get(n); if (!cid) return;
        const x = g.getNodeAttribute(n,'x'); const y = g.getNodeAttribute(n,'y');
        const c = centroids[cid] || {x:0,y:0,count:0}; c.x+=x; c.y+=y; c.count++; centroids[cid] = c;
      });
      Object.keys(centroids).forEach(k => { centroids[k].x/=centroids[k].count; centroids[k].y/=centroids[k].count; });
      const project = (x:number,y:number) => sigmaInst.graphToViewport({x,y});
      const DPR = window.devicePixelRatio;
      // Bundled groups
      if (bundling && state.groups) {
        (state.groups as Map<string, any>).forEach((grp:any) => {
          const c1 = centroids[grp.cidA]; const c2 = centroids[grp.cidB];
            if (!c1 || !c2) return;
          const p1 = project(c1.x, c1.y); const p2 = project(c2.x, c2.y);
          const midx = (p1.x+p2.x)/2; const midy = (p1.y+p2.y)/2;
          const dx = p2.x - p1.x; const dy = p2.y - p1.y;
          const len = Math.sqrt(dx*dx+dy*dy) || 1;
          const nx = -dy/len; const ny = dx/len; // perpendicular
          const curveAmp = Math.min(120, 40 + Math.log(grp.count+1)*25);
          const cx = midx + nx * curveAmp; const cy = midy + ny * curveAmp;
          // Determine dominant relation color if clear majority
          let stroke = '';
          const relEntries = Object.entries(grp.relations) as [string, number][];
          relEntries.sort((a: [string, number], b: [string, number])=> b[1]-a[1]);
          if (relEntries.length && relEntries[0][1] / grp.count > 0.55) {
            stroke = relationColors[relEntries[0][0]] || '';
          }
          if (!stroke) {
            const hue = hashHue(grp.key);
            stroke = `hsl(${hue},70%,60%)`;
          }
          const width = Math.min(10, 0.8 + Math.log(grp.count+1));
          const alpha = 0.35 + Math.min(0.55, (grp.avgConf||0.6)*0.5);
          ctx.strokeStyle = stroke.replace('hsl','hsla').replace(')',`,`+alpha+`)`);
          ctx.lineWidth = width * DPR;
          ctx.beginPath();
          ctx.moveTo(p1.x*DPR, p1.y*DPR);
          ctx.quadraticCurveTo(cx*DPR, cy*DPR, p2.x*DPR, p2.y*DPR);
          ctx.stroke();
          if (showEdgeLabels && cam.getState().ratio > 1.0) {
            ctx.fillStyle = 'rgba(255,255,255,0.75)';
            ctx.font = `${11*DPR}px sans-serif`;
            const txt = relEntries.length ? `${relEntries[0][0]} x${grp.count}` : String(grp.count);
            ctx.fillText(txt, (midx*0.6+cx*0.4)*DPR, (midy*0.6+cy*0.4)*DPR);
          }
        });
      } else {
        // Mild curvature for individual cross-cluster edges to reduce overlap
        g.forEachEdge((e:any) => {
          if (g.getEdgeAttribute(e,'hidden')) return; // skip hidden
          const s = g.source(e); const t = g.target(e);
          const cs = nodeClusterMapRef.current.get(s);
          const ct = nodeClusterMapRef.current.get(t);
          const x1 = g.getNodeAttribute(s,'x'); const y1 = g.getNodeAttribute(s,'y');
          const x2 = g.getNodeAttribute(t,'x'); const y2 = g.getNodeAttribute(t,'y');
          const p1 = project(x1,y1); const p2 = project(x2,y2);
          let curve = 0; if (cs && ct && cs !== ct) curve = 35; // larger curvature cross-cluster
          else curve = 18; // subtle intra-cluster
          // deterministic perpendicular direction
          const dx = p2.x - p1.x; const dy = p2.y - p1.y; const len = Math.sqrt(dx*dx+dy*dy)||1;
          const nx = -dy/len; const ny = dx/len;
          const hash = hashHue(e);
          const sign = (hash % 2 === 0) ? 1 : -1;
          const cx = (p1.x+p2.x)/2 + nx * curve * sign;
          const cy = (p1.y+p2.y)/2 + ny * curve * sign;
          const color = g.getEdgeAttribute(e,'color') || '#8892a0';
          const conf = g.getEdgeAttribute(e,'confidence') || 0.6;
          const baseAlpha = 0.25 + Math.min(0.55, conf * 0.7);
          // convert hex to rgba if needed
          let stroke = color;
          if (/^#/.test(color) && (color.length===7 || color.length===4)) {
            // simple hex -> rgba
            const hex = color.length===7? color.slice(1): color.slice(1).split('').map((c:string)=>c+c).join('');
            const r = parseInt(hex.slice(0,2),16); const gch = parseInt(hex.slice(2,4),16); const b = parseInt(hex.slice(4,6),16);
            stroke = `rgba(${r},${gch},${b},${baseAlpha})`;
          }
          ctx.strokeStyle = stroke;
          ctx.lineWidth = (g.getEdgeAttribute(e,'size') || 1) * DPR;
          ctx.beginPath();
          ctx.moveTo(p1.x*DPR, p1.y*DPR);
          ctx.quadraticCurveTo(cx*DPR, cy*DPR, p2.x*DPR, p2.y*DPR);
          ctx.stroke();
          if (showEdgeLabels && cam.getState().ratio > 1.8) {
            ctx.fillStyle = 'rgba(255,255,255,0.7)';
            ctx.font = `${10*DPR}px sans-serif`;
            const lbl = g.getEdgeAttribute(e,'label');
            if (lbl) ctx.fillText(lbl, cx*DPR, cy*DPR);
          }
        });
      }
    };
    draw();
    const camera = sigmaRef.current.getCamera();
    const onCam = () => { requestAnimationFrame(draw); };
    camera.on('updated', onCam);
    window.addEventListener('resize', draw);
    const interval = setInterval(draw, 1800); // periodic refresh as nodes move/stream
    return () => { camera.off('updated', onCam); window.removeEventListener('resize', draw); clearInterval(interval); };
  }, [bundling, showEdgeLabels]);

  const summarizeSelectedClusters = useCallback(async () => {
    if (!clusters.length) return;
    try {
      const body = { namespace: activeNamespace, cluster_ids: clusters.slice(0, Math.min(5, clusters.length)).map(c => c.id) };
      const res = await fetch('/api/smart-assistant/graphrag/cluster/summarize', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
      if (res.ok) {
        const data = await res.json();
        setClusterSummaries(data.summaries || {});
      }
    } catch (e) {}
  }, [clusters, activeNamespace]);

  // Initial load strategy: progressive nodes instead of sample for Phase 2
  useEffect(() => { loadNodesPage(true); }, [activeNamespace]);

  // SSE stream subscription (Phase 7 completion)
  useEffect(() => {
    let es: EventSource | null = null;
    try {
      es = new EventSource('/api/smart-assistant/graphrag/stream');
      es.onopen = () => setStreamConnected(true);
      es.onerror = () => { setStreamConnected(false); };
      es.onmessage = (ev: MessageEvent) => {
        // Generic fallback
      };
      es.addEventListener('node_added', (ev: any) => {
        try {
          const payload = JSON.parse(ev.data || '{}');
          const g = graphRef.current;
          if (!g.hasNode(payload.id)) {
            g.addNode(payload.id, {
              label: payload.name || payload.id,
              size: 6,
              color: palette.entity,
              x: Math.random() - 0.5,
              y: Math.random() - 0.5,
              raw: { id: payload.id, name: payload.name, label: payload.label || 'Entity', properties: {} }
            });
            sigmaRef.current?.refresh();
          }
        } catch {}
      });
      es.addEventListener('edges_added', (ev: any) => {
        // We only received count summary for now; could refetch edges if needed
      });
    } catch {}
    return () => { try { es?.close(); } catch {} };
  }, []);

  // Snapshot helpers
  const fetchSnapshots = useCallback(async () => {
    try {
      const r = await fetch('/api/smart-assistant/graphrag/snapshots');
      if (r.ok) {
        const d = await r.json();
        setSnapshots(d.snapshots || []);
      }
    } catch {}
  }, []);
  useEffect(() => { fetchSnapshots(); }, [fetchSnapshots]);
  const createSnapshot = useCallback(async () => {
    setCreatingSnapshot(true);
    try {
      const r = await fetch('/api/smart-assistant/graphrag/snapshots', { method:'POST' });
      if (r.ok) { await fetchSnapshots(); }
    } catch {}
    finally { setCreatingSnapshot(false); }
  }, [fetchSnapshots]);
  const diffLatestTwo = useCallback(async () => {
    if (snapshots.length < 2) return;
    const [a,b] = [snapshots[snapshots.length-2].id, snapshots[snapshots.length-1].id];
    try {
      const r = await fetch(`/api/smart-assistant/graphrag/snapshots/diff?a=${a}&b=${b}`);
      if (r.ok) setSnapshotDiff(await r.json());
    } catch {}
  }, [snapshots]);

  // Provenance fetch
  const fetchProvenance = useCallback(async (nid: string) => {
    try {
      const r = await fetch(`/api/smart-assistant/graphrag/provenance?node_id=${encodeURIComponent(nid)}`);
      if (r.ok) {
        const d = await r.json();
        setProvenance(d);
        setShowProvenance(true);
      }
    } catch {}
  }, []);

  // Debounced search
  useEffect(() => {
    if (searchTimeout.current) window.clearTimeout(searchTimeout.current);
    searchTimeout.current = window.setTimeout(() => runSearch(searchQuery), 300);
  }, [searchQuery, runSearch]);

  useEffect(() => { highlightSearchResults(); }, [highlightSearchResults]);

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', background: palette.background, color: '#fff' }}>
      <div ref={containerRef} style={{ flex: 1, position: 'relative' }}>
        <canvas ref={hullCanvasRef} style={{ position:'absolute', inset:0, pointerEvents:'none' }} />
  <canvas ref={curveCanvasRef} style={{ position:'absolute', inset:0, pointerEvents:'none' }} />
        {(loading || loadingMore) && (
          <div style={{ position:'absolute', top:0, left:0, right:0, bottom:0, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(18,22,28,0.35)', backdropFilter:'blur(2px)', fontSize:13 }}>
            <div style={{ padding:12, background:'#1d2430', border:'1px solid #333', borderRadius:6 }}>
              {loadingMore ? 'Loading more…' : 'Loading…'}
            </div>
          </div>) }
      </div>
      <div style={{ width: 300, borderLeft: '1px solid #222', padding: '0.75rem', fontSize: 14 }}>
        <h3 style={{ marginTop: 0 }}>Graph Viewer</h3>
        <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
          <button onClick={() => loadNodesPage(true)} disabled={loadingMore}>{loadingMore ? 'Loading' : 'Reload'}</button>
          <button onClick={() => { setPathMode(p => !p); setSelectedNode(null); setSecondNode(null); setPathResult(null); colorReset(); }} style={{ background: pathMode ? '#444' : '#222' }}>Path</button>
        </div>
        <div style={{ display:'flex', gap:4, marginBottom:8 }}>
          <button disabled={!hasMore || loadingMore} onClick={() => loadNodesPage(false)} style={{ flex:1 }}>{hasMore ? (loadingMore ? 'Loading…' : 'Load More') : 'No More'}</button>
          <button onClick={() => { setError(null); colorReset(); highlightPath(pathResult); }} style={{ flex:1 }}>Reset Colors</button>
        </div>
        <div style={{ display:'flex', gap:4, marginBottom:8 }}>
          <button onClick={() => setShowChunks(s=>!s)} style={{ flex:1, background: showChunks? '#444':'#222' }}>{showChunks? 'Hide Chunks':'Show Chunks'}</button>
          <button onClick={() => setShowEdgeLabels(s=>!s)} style={{ flex:1, background: showEdgeLabels? '#444':'#222' }}>{showEdgeLabels? 'Hide Labels':'Labels'}</button>
          <button onClick={() => setLabelDensity(d=> d==='auto'?'all':'auto')} style={{ flex:1, background: labelDensity==='auto'? '#444':'#222' }}>{labelDensity==='auto'?'Sparse':'All'}</button>
          <button onClick={() => setBundling(b=>!b)} style={{ flex:1, background: bundling? '#444':'#222' }}>{bundling?'Unbundle':'Bundle'}</button>
        </div>
        <div style={{ marginBottom:8 }}>
          <label style={{ display:'block', fontSize:12, opacity:0.7 }}>Relation Filter</label>
          <select value={relationFilter} onChange={(e)=> { setRelationFilter(e.target.value); fetchSample(); }} style={{ width:'100%' }}>
            <option value='*'>All</option>
            {availableRelations.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div style={{ display:'flex', gap:4, marginBottom:8 }}>
          <button style={{ flex:1 }} onClick={async ()=> { await fetch('/api/smart-assistant/graphrag/layout/recompute', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ mode:'clustered' }) }); fetchSample(); }}>Cluster Layout</button>
          <button style={{ flex:1 }} onClick={async ()=> { await fetch('/api/smart-assistant/graphrag/layout/recompute', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ mode:'hybrid' }) }); fetchSample(); }}>Hybrid Layout</button>
          <button style={{ flex:1 }} onClick={recomputeCentrality}>Centrality</button>
        </div>
  <div style={{ marginBottom:8, fontSize:11, opacity:0.7 }}>Live Stream: {streamConnected ? 'connected' : 'offline'}</div>
        <div style={{ marginBottom: 8 }}>
          <label style={{ display:'block', fontSize:12, opacity:0.8 }}>Namespace</label>
          <select value={activeNamespace || ''} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setActiveNamespace(e.target.value || undefined); }} style={{ width: '100%' }}>
            <option value=''>All</option>
            {namespaces.map(ns => <option key={ns} value={ns}>{ns}</option>)}
          </select>
        </div>
        <div style={{ marginBottom: 8 }}>
          <input placeholder='Search nodes...' value={searchQuery} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)} style={{ width:'100%', padding:4, background:'#1d2430', border:'1px solid #333', color:'#fff' }} />
          {searchResults.length > 0 && (
            <div style={{ maxHeight:120, overflowY:'auto', background:'#1b2028', border:'1px solid #333', marginTop:4 }}>
              {searchResults.map(r => (
                <div key={r.id} style={{ padding:'4px 6px', cursor:'pointer', fontSize:12 }} onClick={() => { setSelectedNode(r.id); setSearchQuery(r.name); setSearchResults([]); }}>
                  {r.name} <span style={{ opacity:0.6 }}>({r.label})</span>
                </div>
              ))}
            </div>
          )}
        </div>
        {error && <div style={{ color: '#F4664A', marginBottom: 8 }}>{error}</div>}
        {selectedNode && graphRef.current.hasNode(selectedNode) && (
          <div>
            <h4>Selected</h4>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(graphRef.current.getNodeAttribute(selectedNode, 'raw'), null, 2)}</pre>
            <div style={{ display:'flex', gap:6 }}>
              <button onClick={() => fetchSimilar(selectedNode!)} style={{ flex:1 }}>Semantic Ring</button>
              <button onClick={() => setSemanticRingIds(new Set())} style={{ flex:1 }}>Clear Ring</button>
            </div>
            <div style={{ display:'flex', gap:6, marginTop:4 }}>
              <button onClick={() => runAnswer(graphRef.current.getNodeAttribute(selectedNode,'raw')?.name || 'Show related context')} style={{ flex:1 }}>Answer Context</button>
              <button onClick={() => { setAnswerOverlayIds(new Set()); fetchSimilar(selectedNode!); }} style={{ flex:1 }}>Refresh Both</button>
            </div>
            <div style={{ display:'flex', gap:6, marginTop:4 }}>
              <button onClick={() => fetchProvenance(selectedNode!)} style={{ flex:1 }}>Provenance</button>
              <button onClick={() => { setShowProvenance(false); setProvenance(null); }} style={{ flex:1 }}>Hide Prov</button>
            </div>
          </div>
        )}
        {pathMode && selectedNode && !secondNode && <div style={{ fontSize:12, marginTop:4 }}>Select second node...</div>}
        {pathMode && selectedNode && secondNode && pathResult && (
          <div style={{ marginTop:8 }}>
            <h4>Path</h4>
            <div style={{ fontSize:12 }}>{pathResult.path.join(' -> ')}</div>
            <div style={{ fontSize:11, opacity:0.7 }}>Length: {pathResult.path.length}</div>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <strong>Legend</strong>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            <li><span style={{ background: palette.entity, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Entity</li>
            <li><span style={{ background: palette.technology, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Technology</li>
            <li><span style={{ background: palette.organization, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Organization</li>
            <li><span style={{ background: palette.role, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Role</li>
            <li><span style={{ background: palette.achievement, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Achievement</li>
            <li><span style={{ background: palette.section, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Section</li>
            <li><span style={{ background: palette.chunk, display: 'inline-block', width: 12, height: 12, marginRight: 6 }} />Chunk</li>
            <li style={{ fontSize: 12, opacity: 0.7 }}>Edges: relation = label</li>
          </ul>
        </div>
        <div style={{ marginTop: 12 }}>
          <strong>Clusters</strong>
          <div style={{ fontSize:11, opacity:0.7, marginBottom:4 }}>{clustersLoading ? 'Loading…' : `${clusters.length} clusters`}</div>
          <button style={{ width:'100%', marginBottom:4 }} disabled={!clusters.length} onClick={summarizeSelectedClusters}>Summarize (top {Math.min(5, clusters.length)})</button>
          <div style={{ maxHeight:140, overflowY:'auto', fontSize:11, lineHeight:1.25 }}>
            {clusters.slice(0,12).map(c => (
              <div key={c.id} style={{ padding:'4px 4px', borderBottom:'1px solid #222' }}>
                <div><strong>{clusterSummaries[c.id]?.label || c.id}</strong> <span style={{ opacity:0.6 }}>({c.size})</span></div>
                <div style={{ opacity:0.75 }}>{clusterSummaries[c.id]?.summary ? clusterSummaries[c.id].summary.slice(0,120)+'…' : (c.sample_nodes||[]).join(', ')}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop:8, fontSize:11, opacity:0.7 }}>Zoom: {zoomLevel.toFixed(2)} (LOD: {zoomLevel > 2.0 ? 'detail' : zoomLevel > 1.2 ? 'mixed' : 'clusters'})</div>
          <div style={{ marginTop:4, fontSize:11, opacity:0.7 }}>FPS: {fps} {degraded ? '(degraded)' : ''}</div>
        </div>
        <div style={{ marginTop:16 }}>
          <strong>Snapshots</strong>
          <div style={{ marginTop:4 }}>
            <button onClick={createSnapshot} disabled={creatingSnapshot} style={{ width:'100%' }}>{creatingSnapshot ? 'Creating…' : 'Create Snapshot'}</button>
          </div>
          <div style={{ marginTop:4 }}>
            <button onClick={diffLatestTwo} disabled={snapshots.length<2} style={{ width:'100%' }}>Diff Last Two</button>
          </div>
          <div style={{ maxHeight:140, overflowY:'auto', fontSize:11, marginTop:4, border:'1px solid #222', padding:4 }}>
            {snapshots.slice().reverse().map(s => (
              <div key={s.id} style={{ padding:'3px 2px', borderBottom:'1px solid #222' }}>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ opacity:0.85 }}>{s.node_count}N/{s.edge_count}E</span>
                  <span style={{ opacity:0.6 }}>{(s.created_at||'').split('T')[1]?.slice(0,8)}</span>
                </div>
                <div style={{ fontSize:10, opacity:0.6 }}>{s.id.slice(0,8)}… mod:{s.modularity ?? '—'}</div>
              </div>
            ))}
          </div>
          {snapshotDiff && (
            <div style={{ marginTop:6, fontSize:11, background:'#1d2430', padding:6 }}>
              <div><strong>Diff</strong> ΔN {snapshotDiff.delta_nodes} | ΔE {snapshotDiff.delta_edges} | ΔMod {snapshotDiff.delta_modularity?.toFixed ? snapshotDiff.delta_modularity.toFixed(3) : snapshotDiff.delta_modularity}</div>
              <div style={{ maxHeight:80, overflowY:'auto', fontSize:10 }}>
                Added Clusters: {Object.keys(snapshotDiff.clusters?.added||{}).length} | Removed: {Object.keys(snapshotDiff.clusters?.removed||{}).length}
              </div>
            </div>
          )}
        </div>
        {showProvenance && provenance && (
          <div style={{ marginTop:16 }}>
            <strong>Provenance</strong>
            <div style={{ fontSize:11, opacity:0.8, marginTop:4 }}>Neighbors ({(provenance.neighbors||[]).length})</div>
            <div style={{ maxHeight:70, overflowY:'auto', fontSize:10 }}>
              {(provenance.neighbors||[]).map((n:any) => <div key={n.id}>{n.name||n.id}</div>)}
            </div>
            <div style={{ fontSize:11, opacity:0.8, marginTop:6 }}>Chunks</div>
            <div style={{ maxHeight:80, overflowY:'auto', fontSize:10 }}>
              {(provenance.chunks||[]).map((c:any) => <div key={c.id}>{(c.text||'').slice(0,90)}…</div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphViewer;
