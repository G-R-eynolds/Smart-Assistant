import pytest
import asyncio
from app.core.graphrag_query_adapter import query_adapter
from app.core import database as db

@pytest.fixture(scope="module", autouse=True)
def init_db():
    # Initialize database once for tests
    asyncio.run(db.init_db())
    yield

@pytest.mark.asyncio
async def test_query2_auto_mode():
    res = await query_adapter.query(query="test entity relationship", mode="auto", top_k=3)
    assert res["success"] is True
    assert res["mode_used"] in {"local", "global"}

@pytest.mark.asyncio
async def test_query2_explicit_modes():
    for m in ["global", "local", "drift"]:
        res = await query_adapter.query(query="short", mode=m, top_k=2)
        assert res["success"] is True
        assert res["mode_used"] == m
