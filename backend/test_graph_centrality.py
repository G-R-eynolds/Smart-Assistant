import asyncio, os, pytest
from app.core.database import init_db, get_db_session
from app.core.graphrag_service import graphrag_service
from sqlalchemy import select
from app.models.database import GraphNode

pytestmark = pytest.mark.asyncio

doc_text = """EXPERIENCE\nAcme Corp Senior Engineer working with Python Docker Kubernetes.\nResearch on Graph Algorithms and Network Optimization.\n"""

async def test_centrality_computation():
    os.makedirs('data', exist_ok=True)
    if os.path.exists('data/webui.db'):
        os.remove('data/webui.db')
    await init_db()
    r = await graphrag_service.ingest_document(doc_id='cent::1', text=doc_text, metadata={})
    assert r.get('success')
    c = await graphrag_service.compute_centrality()
    assert c.get('success')
    async with get_db_session() as session:
        res = await session.execute(select(GraphNode))
        nodes = res.scalars().all()
        has_importance = any(((n.properties or {}).get('importance') is not None) for n in nodes)
        assert has_importance, 'Expected some nodes to have importance after centrality compute'
