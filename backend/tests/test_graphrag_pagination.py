import pytest
import pytest_asyncio
import httpx
from app.main import app
from app.core.database import init_db, close_db, get_db_session
from app.models.database import GraphNode, GraphEdge
from sqlalchemy import delete
from uuid import uuid4
import random

DEFAULT_NS = "public"

@pytest_asyncio.fixture(scope="module", autouse=True)
async def _db_seed():
    await init_db()
    # Seed sample nodes & edges
    async with get_db_session() as session:
        # Clear existing graph data to avoid unique constraint conflicts
        await session.execute(delete(GraphEdge))
        await session.execute(delete(GraphNode))
        nodes = []
        for i in range(15):
            nid = f"N{i}"  # stable ids for ordering
            node = GraphNode(
                id=nid,
                label="Entity" if i % 3 else "Chunk",
                name=f"Node {i:02d}",
                properties={"namespace": DEFAULT_NS, "layout": {"x": (i - 7)/5, "y": ((i % 5) - 2)/4}}
            )
            session.add(node)
            nodes.append(node)
        for i in range(14):
            e = GraphEdge(
                id=f"E{i}",
                source_id=f"N{i}",
                target_id=f"N{i+1}",
                relation="LINKS_TO",
                confidence=0.9,
                properties={"namespace": DEFAULT_NS}
            )
            session.add(e)
        await session.commit()
    yield
    await close_db()

@pytest.mark.asyncio
async def test_nodes_pagination_basic():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get("/api/smart-assistant/graphrag/nodes", params={"limit": 5})
        assert r1.status_code == 200
        data1 = r1.json()
        assert "results" in data1
        cursor = data1.get("cursor")
        assert len(data1["results"]) <= 5
        assert cursor is not None  # more pages expected
        last_id_page1 = data1["results"][-1]["id"] if data1["results"] else None
        r2 = await ac.get("/api/smart-assistant/graphrag/nodes", params={"limit":5, "cursor": cursor})
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["results"]
        # Ensure progression: first id of page2 should not equal first id of page1
        assert data1["results"][0]["id"] != data2["results"][0]["id"]
        # And first id of page2 should not be the same as last id of page1
        if last_id_page1:
            assert data2["results"][0]["id"] != last_id_page1

@pytest.mark.asyncio
async def test_edges_filter_node_ids():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # First get a few nodes
        rn = await ac.get("/api/smart-assistant/graphrag/nodes", params={"limit": 3})
        assert rn.status_code == 200
        nodes = rn.json().get("results", [])
        if len(nodes) >= 2:
            id_list = ",".join([n["id"] for n in nodes[:2]])
            re = await ac.get("/api/smart-assistant/graphrag/edges", params={"limit": 50, "node_ids": id_list})
            assert re.status_code == 200
            edata = re.json()
            assert "results" in edata
            for e in edata["results"]:
                assert e["source_id"] or e["target_id"]

@pytest.mark.asyncio
async def test_viewport_mode_subset():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/smart-assistant/graphrag/graph", params={"mode": "viewport", "x": 0, "y": 0, "wx": 1.5, "wy": 1.5, "sample": 50})
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        # viewport sample should not exceed requested sample
        assert len(data["nodes"]) <= 50
