from app.core.graphrag_query_adapter import query_adapter
from app.core.graphrag_service import graphrag_service
import pytest, asyncio
from app.core import database as db

@pytest.fixture(scope="module", autouse=True)
def init_db():
    asyncio.run(db.init_db())
    yield

@pytest.mark.asyncio
async def test_query2_metrics_increment():
    before = graphrag_service.metrics.get("query2_latency_count", 0)
    await query_adapter.query("sample test query", mode="auto", top_k=2)
    after = graphrag_service.metrics.get("query2_latency_count", 0)
    assert after == before + 1
