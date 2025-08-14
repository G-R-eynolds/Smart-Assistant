import pytest, httpx, asyncio
from sqlalchemy import delete
from app.core.database import init_db, get_db_session
from app.models.database import GraphNode, GraphEdge
from app.main import app

@pytest.mark.asyncio
async def test_summary_budget_rate_limit():
    await init_db()
    # Seed minimal cluster graph
    async with get_db_session() as session:
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        for i in range(3):
            session.add(GraphNode(id=f"n{i}", label="Entity", name=f"Term{i}", namespace="public", properties={"namespace":"public"}))
        await session.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Force compute
        r = await client.get('/api/smart-assistant/graphrag/cluster?namespace=public&force=true')
        assert r.status_code == 200
        cid = r.json()['clusters'][0]['id'] if r.json()['clusters'] else 'c1'
        # Hit summarize many times quickly to trigger rate limit at some point
        exceeded = False
        for _ in range(25):
            sr = await client.post('/api/smart-assistant/graphrag/cluster/summarize', json={"namespace":"public","cluster_ids":[cid]})
            assert sr.status_code == 200
            if 'rate limit' in str(sr.json()).lower():
                exceeded = True
                break
        assert exceeded, 'Expected rate limit to trigger'
