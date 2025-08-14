import asyncio
import pytest

from app.core.job_deduplication import job_deduplication_service
from app.core.database import init_db, close_db
from app.core.config import settings

pytestmark = pytest.mark.asyncio

async def test_filter_new_jobs_basic(tmp_path, monkeypatch):
    # Use a temporary SQLite DB for this test
    db_path = tmp_path / "test.db"
    # Override runtime settings directly (settings object is created at import time)
    settings.DATABASE_URL = f"sqlite:///{db_path}"

    await init_db()
    try:
        jobs = [
            {"title": "SE", "company": "A", "url": "https://x/jobs/1"},
            {"title": "SE", "company": "B", "url": "https://x/jobs/2"},
        ]
        # Initially none processed
        new_jobs = await job_deduplication_service.process_jobs_with_deduplication(jobs)
        assert len(new_jobs) == 2

        # Mark as processed
        await job_deduplication_service.mark_jobs_as_processed(new_jobs)

        # Next run should filter all
        again = await job_deduplication_service.process_jobs_with_deduplication(jobs)
        assert len(again) == 0
    finally:
        await close_db()
