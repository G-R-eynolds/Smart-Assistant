// Placeholder Web Worker for future offloaded layout (Phase 5)
// Receives: {type:'layout', nodes:[{id,x,y}], edges:[...]} and returns updated positions.
self.onmessage = (e) => {
  const data = e.data || {};
  if (data.type === 'layout') {
    // No-op simple jitter to simulate work
    const updated = (data.nodes||[]).map(n => ({...n, x: n.x * 0.999 + 0.001, y: n.y * 0.999 - 0.001}));
    self.postMessage({ type: 'layoutResult', nodes: updated, version: data.version || Date.now() });
  }
};
