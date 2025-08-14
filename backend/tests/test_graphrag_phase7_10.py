import pytest, httpx, asyncio
from app.core.database import init_db, get_db_session
from sqlalchemy import delete
from app.models.database import GraphNode, GraphEdge
from app.main import app

@pytest.mark.asyncio
async def test_path_and_similarity_and_metrics():
    await init_db()
    # Seed simple line A-B-C-D plus embeddings
    async with get_db_session() as session:
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        nodes = [
            GraphNode(id='A', label='Entity', name='Alpha', namespace='public', properties={'namespace':'public'}, embedding=[1,0,0]),
            GraphNode(id='B', label='Entity', name='Beta', namespace='public', properties={'namespace':'public'}, embedding=[0.9,0.1,0]),
            GraphNode(id='C', label='Entity', name='Gamma', namespace='public', properties={'namespace':'public'}, embedding=[0,1,0]),
            GraphNode(id='D', label='Entity', name='Delta', namespace='public', properties={'namespace':'public'}, embedding=[0,0.9,0.1]),
        ]
        for n in nodes: session.add(n)
        edges = [
            GraphEdge(id='eAB', source_id='A', target_id='B', relation='LINKS', confidence=0.9, properties={'namespace':'public'}),
            GraphEdge(id='eBC', source_id='B', target_id='C', relation='LINKS', confidence=0.9, properties={'namespace':'public'}),
            GraphEdge(id='eCD', source_id='C', target_id='D', relation='LINKS', confidence=0.9, properties={'namespace':'public'}),
        ]
        for e in edges: session.add(e)
        await session.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        # Path
        pr = await client.post('/api/smart-assistant/graphrag/path', json={'source_id':'A','target_id':'D','max_depth':5})
        assert pr.status_code == 200
        pdata = pr.json()
        assert pdata['path'] == ['A','B','C','D']
        # Similar (embedding based)
        sr = await client.get('/api/smart-assistant/graphrag/similar?node_id=A&top_k=2')
        assert sr.status_code == 200
        sdata = sr.json()
        assert sdata['similar'] and sdata['similar'][0]['id'] in ['B','C']
        # Namespaces
        nr = await client.get('/api/smart-assistant/graphrag/namespaces')
        assert nr.status_code == 200
        assert 'public' in nr.json().get('namespaces', [])
        # Metrics
        mr = await client.get('/api/smart-assistant/graphrag/metrics')
        assert mr.status_code == 200
        assert 'metrics' in mr.json()

