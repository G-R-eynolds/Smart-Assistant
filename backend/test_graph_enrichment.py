import asyncio
import os
import pytest
from app.core.graphrag_service import graphrag_service
from app.core.database import init_db

pytestmark = pytest.mark.asyncio

TEST_DOC = """EXPERIENCE\nAcme Corporation Lead Engineer built scalable Python microservices using Docker and Kubernetes.\nProjects included Graph Optimization and Transformer fine-tuning with PyTorch.\n"""

async def _ingest():
    r = await graphrag_service.ingest_document(doc_id="test::doc1", text=TEST_DOC, metadata={"source":"unit"})
    assert r.get("success"), r
    return r


async def _fetch_nodes():
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode
    async with get_db_session() as session:
        res = await session.execute(select(GraphNode))
        return res.scalars().all()

async def _fetch_edges():
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphEdge
    async with get_db_session() as session:
        res = await session.execute(select(GraphEdge))
        return res.scalars().all()

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

async def test_enrichment_and_layout():
    # Ensure DB initialized (and parent directory exists)
    os.makedirs("data", exist_ok=True)
    await init_db()
    await _ingest()
    nodes = await _fetch_nodes()
    edges = await _fetch_edges()
    # Basic expectations: classification labels present
    labels = {n.label for n in nodes}
    assert any(l in labels for l in ["Technology","Organization","Role"]) or "Entity" in labels
    # Derived relations
    rels = {e.relation for e in edges}
    assert "CO_OCCURS" in rels or "HAS_ENTITY" in rels
    # Layout coordinates exist for at least some nodes
    with_layout = [n for n in nodes if (n.properties or {}).get("layout", {}).get("x") is not None]
    assert with_layout, "Expected at least one node with layout coordinates"
    # Degree data persisted
    deg_values = [ (n.properties or {}).get("degree") for n in nodes if (n.properties or {}).get("degree") is not None ]
    assert deg_values, "Expected degree values persisted"
