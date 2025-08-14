import pytest
import asyncio
import httpx
from sqlalchemy import delete
from app.core.database import init_db, get_db_session
from app.models.database import GraphNode, GraphEdge
from app.main import app

@pytest.mark.asyncio
async def test_cluster_compute_and_summary():
    await init_db()
    # Seed small graph with two obvious clusters
    async with get_db_session() as session:
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        # Cluster A
        for i in range(5):
            session.add(GraphNode(id=f"a{i}", label="Entity", name=f"Alpha {i}", namespace="public", properties={"namespace":"public"}))
        # Dense edges within A
        for i in range(5):
            for j in range(i+1,5):
                session.add(GraphEdge(id=f"ea{i}{j}", source_id=f"a{i}", target_id=f"a{j}", relation="LINKS", confidence=0.9, properties={"namespace":"public"}))
        # Cluster B
        for i in range(5):
            session.add(GraphNode(id=f"b{i}", label="Entity", name=f"Beta {i}", namespace="public", properties={"namespace":"public"}))
        for i in range(5):
            for j in range(i+1,5):
                session.add(GraphEdge(id=f"eb{i}{j}", source_id=f"b{i}", target_id=f"b{j}", relation="LINKS", confidence=0.9, properties={"namespace":"public"}))
        await session.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/smart-assistant/graphrag/cluster?namespace=public&force=true")
        assert r.status_code == 200
        data = r.json()
        assert data["stats"]["clusters"] >= 2
        # Summaries (will fallback if LLM not configured)
        cluster_ids = [c['id'] for c in data['clusters'][:2]]
        sr = await client.post("/api/smart-assistant/graphrag/cluster/summarize", json={"namespace":"public","cluster_ids": cluster_ids})
        assert sr.status_code == 200
        sdata = sr.json()
        for cid in cluster_ids:
            assert cid in sdata['summaries']
