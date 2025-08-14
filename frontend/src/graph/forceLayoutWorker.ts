// Simple force-directed layout worker (placeholder iterative simulation)
// Receives { type:'init', nodes:[{id,x,y}], edges:[{source,target}] }
// and { type:'tick' } commands; posts back { type:'positions', nodes:[{id,x,y}] }

interface Node { id: string; x: number; y: number; vx?: number; vy?: number; }
interface Edge { source: string; target: string; }

let nodes: Node[] = [];
let edges: Edge[] = [];

const conf = { repulsion: 200, spring: 0.02, damping: 0.85, step: 0.02 };

function simulateStep() {
  // Repulsion
  for (let i=0;i<nodes.length;i++) {
    const n1 = nodes[i];
    n1.vx = n1.vx || 0; n1.vy = n1.vy || 0;
    for (let j=i+1;j<nodes.length;j++) {
      const n2 = nodes[j];
      const dx = n1.x - n2.x;
      const dy = n1.y - n2.y;
      let dist2 = dx*dx + dy*dy + 0.01;
      const f = conf.repulsion / dist2;
      const fx = f * dx; const fy = f * dy;
      n1.vx += fx; n1.vy += fy;
  n2.vx = (n2.vx||0) - fx; n2.vy = (n2.vy||0) - fy;
    }
  }
  // Springs
  for (const e of edges) {
    const a = nodes.find(n=>n.id===e.source);
    const b = nodes.find(n=>n.id===e.target);
    if (!a || !b) continue;
    const dx = b.x - a.x; const dy = b.y - a.y;
    const dist = Math.sqrt(dx*dx + dy*dy) || 0.001;
    const target = 1.2;
    const diff = dist - target;
    const f = conf.spring * diff;
    const fx = f * dx/dist; const fy = f * dy/dist;
    a.vx = (a.vx||0) + fx; a.vy = (a.vy||0) + fy;
    b.vx = (b.vx||0) - fx; b.vy = (b.vy||0) - fy;
  }
  // Integrate
  for (const n of nodes) {
    n.vx = (n.vx||0) * conf.damping; n.vy = (n.vy||0) * conf.damping;
    n.x += (n.vx||0) * conf.step; n.y += (n.vy||0) * conf.step;
  }
}

function tick(iterations: number) {
  for (let i=0;i<iterations;i++) simulateStep();
  postMessage({ type:'positions', nodes: nodes.map(n=>({ id:n.id, x:n.x, y:n.y })) });
}

onmessage = (ev: MessageEvent) => {
  const data = ev.data || {};
  if (data.type === 'init') {
    nodes = data.nodes || [];
    edges = data.edges || [];
  } else if (data.type === 'tick') {
    tick(data.iterations || 1);
  }
};
