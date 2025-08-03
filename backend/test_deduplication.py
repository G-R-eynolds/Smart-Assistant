#!/usr/bin/env python3
"""
Test script for job deduplication functionality.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.job_deduplication import job_deduplication_service
from app.core.database import init_db, close_db
from app.core.logging import logger

async def test_job_deduplication():
    """Test the job deduplication service"""
    
    # Initialize database
    await init_db()
    
    print("🧪 Testing Job Deduplication Service")
    print("=" * 50)
    
    # Test data
    test_jobs = [
        {
            "title": "Python Developer",
            "company": "Test Company A",
            "location": "Remote",
            "url": "https://linkedin.com/jobs/view/123456",
            "description": "Python developer position..."
        },
        {
            "title": "Software Engineer",
            "company": "Test Company B", 
            "location": "New York",
            "url": "https://linkedin.com/jobs/view/789012",
            "description": "Software engineer role..."
        },
        {
            "title": "Data Scientist",
            "company": "Test Company C",
            "location": "San Francisco",
            "url": "https://linkedin.com/jobs/view/345678",
            "description": "Data science position..."
        }
    ]
    
    # Test 1: Process jobs for the first time (should be all new)
    print("\n1️⃣ First run - all jobs should be new:")
    new_jobs_round1 = await job_deduplication_service.process_jobs_with_deduplication(test_jobs)
    print(f"   Found {len(new_jobs_round1)} new jobs out of {len(test_jobs)}")
    
    # Mark them as processed
    await job_deduplication_service.mark_jobs_as_processed(new_jobs_round1)
    print(f"   Marked {len(new_jobs_round1)} jobs as processed")
    
    # Test 2: Process same jobs again (should be all duplicates)
    print("\n2️⃣ Second run - all jobs should be duplicates:")
    new_jobs_round2 = await job_deduplication_service.process_jobs_with_deduplication(test_jobs)
    print(f"   Found {len(new_jobs_round2)} new jobs out of {len(test_jobs)}")
    
    # Test 3: Mix of new and old jobs
    mixed_jobs = test_jobs[:2] + [  # 2 old jobs
        {
            "title": "ML Engineer", 
            "company": "Test Company D",
            "location": "Austin",
            "url": "https://linkedin.com/jobs/view/999999",
            "description": "Machine learning engineer..."
        }
    ]  # 1 new job
    
    print("\n3️⃣ Third run - mix of old and new jobs:")
    print(f"   Testing {len(mixed_jobs)} jobs (2 old + 1 new)")
    new_jobs_round3 = await job_deduplication_service.process_jobs_with_deduplication(mixed_jobs)
    print(f"   Found {len(new_jobs_round3)} new jobs")
    
    # Display the new job
    if new_jobs_round3:
        for job in new_jobs_round3:
            print(f"   New job: {job['title']} at {job['company']}")
    
    # Test 4: Check processed URLs count
    print("\n4️⃣ Checking processed URLs:")
    processed_urls = await job_deduplication_service.get_processed_urls()
    print(f"   Total processed URLs in database: {len(processed_urls)}")
    
    # Cleanup
    await close_db()
    
    print("\n✅ Deduplication test completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_job_deduplication())
