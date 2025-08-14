import pytest, httpx
from app.core.database import init_db, get_db_session
from sqlalchemy import delete
from app.models.database import GraphNode, GraphEdge
from app.main import app

@pytest.mark.asyncio
async def test_snapshots_create_list_diff():
    await init_db()
    # seed small graph
    async with get_db_session() as session:
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        session.add(GraphNode(id='N1', label='Entity', name='Node1', namespace='public'))
        session.add(GraphNode(id='N2', label='Entity', name='Node2', namespace='public'))
        session.add(GraphEdge(id='E1', source_id='N1', target_id='N2', relation='LINKS', confidence=0.9))
        await session.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        cr = await client.post('/api/smart-assistant/graphrag/snapshots')
        assert cr.status_code == 200
        sid1 = cr.json()['snapshot_id']
        # add node then second snapshot
        async with get_db_session() as session:
            session.add(GraphNode(id='N3', label='Entity', name='Node3', namespace='public'))
            await session.commit()
        cr2 = await client.post('/api/smart-assistant/graphrag/snapshots')
        sid2 = cr2.json()['snapshot_id']
        # list
        lr = await client.get('/api/smart-assistant/graphrag/snapshots')
        assert lr.status_code == 200
        snaps = lr.json()['snapshots']
        assert any(s['id']==sid1 for s in snaps)
        assert any(s['id']==sid2 for s in snaps)
        # diff
        dr = await client.get(f'/api/smart-assistant/graphrag/snapshots/diff?a={sid1}&b={sid2}')
        assert dr.status_code == 200
        diff = dr.json()
        assert diff['delta_nodes'] >= 1
