import asyncio
import pytest

from app.core import database as db
from app.models.database import IngestLog
from scripts.run_graphrag_index import orchestrate
from app.core.graphrag_query_adapter import query_adapter
from app.core.graphrag_service import graphrag_service


@pytest.fixture(scope="module", autouse=True)
def init_db():
    asyncio.run(db.init_db())
    yield


@pytest.mark.asyncio
async def test_selective_delta_marks_indexed(tmp_path):
    # Seed one stale doc in default namespace
    import uuid
    doc_id = f"docA-{uuid.uuid4().hex[:8]}"
    async with db.get_db_session() as session:  # type: ignore
        row = IngestLog(id=doc_id, namespace="public", content_hash="h1", status="stale")
        session.add(row)
        await session.commit()
    # Run orchestrator (should not NOOP because stale exists)
    # Run orchestrate off the event loop
    res = await asyncio.to_thread(orchestrate, namespace="public", force=False, dry_run=False)
    assert res['status'] in {"SUCCESS", "PARTIAL", "FAILED", "IMPORT_FAILED"}
    # Verify status flipped to indexed
    async with db.get_db_session() as session:  # type: ignore
        from sqlalchemy import select
        q = await session.execute(select(IngestLog).where(IngestLog.id == doc_id))
        got = q.scalars().first()
        assert got is not None
        assert got.status == "indexed"


@pytest.mark.asyncio
async def test_artifact_cache_metrics_increment():
    # Ensure at least one call to populate metrics
    before_hits = graphrag_service.metrics.get('artifact_cache_hits', 0)
    before_misses = graphrag_service.metrics.get('artifact_cache_misses', 0)
    for _ in range(2):
        await query_adapter.query(query="cache test", mode="global", top_k=1)
    after_hits = graphrag_service.metrics.get('artifact_cache_hits', 0)
    after_misses = graphrag_service.metrics.get('artifact_cache_misses', 0)
    # Either hits or misses should increase after queries (depending on artifacts presence)
    assert (after_hits > before_hits) or (after_misses > before_misses)
