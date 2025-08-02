"""
Live Production Test for the Rebuilt LinkedInScraperV2

This test script performs a LIVE job search using the rebuilt LinkedIn scraper
and a real connection to the Bright Data API. It does NOT use mock data.

Purpose:
- To verify the end-to-end scraping functionality is working correctly.
- To validate the structure and quality of the data returned from a live scrape.

Prerequisites:
- A configured .env file with valid Bright Data credentials.
- The 'websockets' and 'pytest' libraries installed in the venv.
"""

import asyncio
import pytest
import sys
import os

# Add the app directory to the Python path to allow for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.linkedin_scraper_v2 import linkedin_scraper_v2
from app.core.config import settings

# --- Test Configuration ---

# A common, high-volume search query to maximize the chance of getting results.
TEST_KEYWORDS = "Software Engineer"
TEST_LOCATION = "Remote"
TEST_LIMIT = 10

# --- Live Test Case ---

@pytest.mark.asyncio
async def test_live_job_scraping_and_data_validation():
    """
    Performs a live search and validates the results.
    This test will fail if Bright Data is not configured or if LinkedIn
    changes its page structure significantly.
    """
    print(f"\n🚀 Running live test: Searching for '{TEST_KEYWORDS}' in '{TEST_LOCATION}'...")

    # Pre-condition check: Ensure credentials are set
    assert settings.BRIGHT_DATA_ENDPOINT, "Bright Data endpoint is not configured."
    assert settings.BRIGHT_DATA_USERNAME, "Bright Data username is not configured."
    assert settings.BRIGHT_DATA_PASSWORD, "Bright Data password is not configured."

    # Act: Perform the live job search
    try:
        jobs = await linkedin_scraper_v2.search_jobs(
            keywords=TEST_KEYWORDS,
            location=TEST_LOCATION,
            limit=TEST_LIMIT
        )
    finally:
        # Ensure the scraper's session is closed after the test
        await linkedin_scraper_v2.close()

    # Assert: Validate the results
    print(f"📊 Found {len(jobs)} jobs.")
    
    # 1. Check that we got some results
    assert isinstance(jobs, list), "The result should be a list."
    assert len(jobs) > 0, f"Expected to find at least one job for '{TEST_KEYWORDS}', but found none."
    assert len(jobs) <= TEST_LIMIT, f"Found more jobs ({len(jobs)}) than the specified limit ({TEST_LIMIT})."

    # 2. Validate the structure of the first job object
    first_job = jobs[0]
    print(f"🔍 Validating first job found: '{first_job.get('title')}' at '{first_job.get('company')}'")
    
    expected_keys = ["id", "title", "company", "location", "url", "description", "posted_at", "source"]
    for key in expected_keys:
        assert key in first_job, f"Key '{key}' is missing from the job data."
        assert first_job[key] is not None, f"Value for key '{key}' should not be None."

    # 3. Validate data cleaning and formatting
    assert first_job['source'] == 'linkedin'
    assert '?' not in first_job['url'], "URL should be cleaned of tracking parameters."
    assert first_job['url'].startswith("https://www.linkedin.com/jobs/view/"), "URL format is incorrect."

    print("✅ Live scraping test passed successfully.")

# --- Standalone Execution ---

async def main():
    """Allows the script to be run directly."""
    try:
        await test_live_job_scraping_and_data_validation()
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    # This allows running the test directly, e.g., `python tests/test_linkedin_scraper_rebuilt.py`
    asyncio.run(main())