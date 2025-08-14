import asyncio
from uuid import uuid4
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, close_db

@pytest.mark.asyncio
async def test_graphrag_heuristic_ingest():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "doc_id": f"unit-{uuid4()}",
            "text": "Gradient Descent optimizes parameters. SGD uses mini-batches.",
            "force_heuristic": True,
            "disable_embeddings": True,
        }
        r = await ac.post("/api/smart-assistant/graphrag/ingest", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        stats = data.get("stats", {})
    assert stats.get("nodes", 0) >= 1
    assert stats.get("edges", 0) >= 1

@pytest.mark.asyncio
async def test_graphrag_answer_empty_context():
    # With minimal data, answer may be empty but endpoint should succeed
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/smart-assistant/graphrag/answer", json={"question": "What is SGD?"})
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
