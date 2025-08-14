import pytest, httpx
from app.core.database import init_db, get_db_session
from sqlalchemy import delete
from app.models.database import GraphNode, GraphEdge
from app.main import app

@pytest.mark.asyncio
async def test_provenance_endpoint():
    await init_db()
    # Simple two entities and a chunk connection
    async with get_db_session() as session:
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        chunk = GraphNode(id='doc1::chunk::0', label='Chunk', name='Chunk 0', properties={'text':'Alpha Beta', 'namespace':'public'})
        a = GraphNode(id='A', label='Entity', name='Alpha', properties={'namespace':'public'})
        b = GraphNode(id='B', label='Entity', name='Beta', properties={'namespace':'public'})
        session.add_all([chunk,a,b])
        e1 = GraphEdge(id='e1', source_id='A', target_id='doc1::chunk::0', relation='MENTIONED_IN', confidence=0.6, properties={'namespace':'public'})
        e2 = GraphEdge(id='e2', source_id='B', target_id='doc1::chunk::0', relation='MENTIONED_IN', confidence=0.6, properties={'namespace':'public'})
        session.add_all([e1,e2])
        await session.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        r = await client.get('/api/smart-assistant/graphrag/provenance', params={'node_id':'A'})
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        assert any('Alpha' in (c.get('text') or '') or 'Alpha' in (c.get('text') or '') for c in data.get('chunks', []))
        # neighbor entity B expected indirectly via shared chunk? Implementation currently focuses on direct edges; may not list B yet.
