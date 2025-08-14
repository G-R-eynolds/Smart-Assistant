import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from app.main import app
from app.core.database import init_db

@pytest.mark.asyncio
async def test_namespace_isolation():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        doc_a = f"na-{uuid4()}"
        doc_b = f"nb-{uuid4()}"
        text = "Alpha Beta Gamma Delta"
        # Ingest into two namespaces
        for ns, did in [("teamA", doc_a), ("teamB", doc_b)]:
            r = await ac.post("/api/smart-assistant/graphrag/ingest", json={
                "doc_id": did,
                "text": text,
                "force_heuristic": True,
                "disable_embeddings": True,
                "namespace": ns,
            })
            assert r.status_code == 200 and r.json()["success"]
        # Query limited to teamA should not see teamB chunk ids
        qa = await ac.post("/api/smart-assistant/graphrag/query", json={"query": "Alpha", "top_k": 10, "namespace": "teamA"})
        qb = await ac.post("/api/smart-assistant/graphrag/query", json={"query": "Alpha", "top_k": 10, "namespace": "teamB"})
        ida = {n['id'] for n in qa.json()['results']['nodes']}
        idb = {n['id'] for n in qb.json()['results']['nodes']}
        assert ida and idb
        assert ida.isdisjoint(idb)

@pytest.mark.asyncio
async def test_metrics_and_path():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Ingest small doc to ensure nodes
        did = f"path-{uuid4()}"
        text = "NodeOne NodeTwo NodeThree"
        r = await ac.post("/api/smart-assistant/graphrag/ingest", json={
            "doc_id": did,
            "text": text,
            "force_heuristic": True,
            "disable_embeddings": True,
        })
        assert r.status_code == 200
        nodes = r.json()["stats"]["nodes"]
        assert nodes >= 1
        # Metrics JSON
        mjson = await ac.get("/api/smart-assistant/graphrag/metrics")
        assert mjson.status_code == 200
        data = mjson.json()["metrics"]
        assert "ingest_count" in data
        # Metrics Prometheus format
        mprom = await ac.get("/api/smart-assistant/graphrag/metrics?format=prom")
        assert mprom.status_code == 200
        assert "graphrag_ingest_count" in mprom.text
        # Path (trivial: same node path)
        # Get a node id
        q = await ac.post("/api/smart-assistant/graphrag/query", json={"query": "NodeOne", "top_k": 1})
        nid = q.json()["results"]["nodes"][0]["id"]
        p = await ac.post("/api/smart-assistant/graphrag/path", json={"source_id": nid, "target_id": nid})
        assert p.status_code == 200
        assert p.json().get("path")
