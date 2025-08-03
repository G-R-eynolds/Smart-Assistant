#!/usr/bin/env python3
"""
Debug script to test Airtable operations specifically.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.airtable_client import AirtableClient
from app.core.logging import logger
import json

async def test_airtable_debug():
    """Test Airtable operations with debug info"""
    
    # Initialize services
    airtable = AirtableClient()
    
    # Create a simple test job
    test_job = {
        "title": "Test Python Developer",
        "company": "Test Company",
        "location": "Remote",
        "url": "https://example.com/job/1",
        "description": "This is a test job description for Python developer position.",
        "source": "linkedin",
        "posted_at": "2025-01-03T10:00:00Z",
        "scraped_at": "2025-01-03T14:43:00Z",
        "id": "test_job_123",
        "relevance_score": 0.85
    }
    
    print("🧪 Testing Airtable with simple job...")
    logger.info(f"Test job data: {json.dumps(test_job, indent=2)}")
    
    try:
        result = await airtable.add_jobs([test_job])
        print("✅ Simple test passed")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Simple test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Now test with a more complex job that includes AI insights
    complex_job = {
        **test_job,
        "title": "Complex Test Python Developer",
        "ai_insights": {
            "match_reasoning": "Strong Python background with ML experience",
            "skills_match": ["Python", "Machine Learning", "AWS"],
            "experience_match": True
        },
        "cover_letter": {
            "cover_letter": "Dear Hiring Manager, I am interested in this position...",
            "generated_at": "2025-01-03T14:45:00Z",
            "success": True
        },
        "job_analysis": {
            "success": True,
            "analysis": {
                "required_skills": ["Python", "Django", "PostgreSQL"],
                "preferred_skills": ["AWS", "Docker"],
                "experience_level": "Mid-level",
                "work_arrangement": "Remote",
                "salary_range": "$80,000 - $120,000",
                "education_requirements": "Bachelor's degree"
            }
        }
    }
    
    print("\n🧪 Testing Airtable with complex job (AI insights, cover letter, analysis)...")
    logger.info(f"Complex job keys: {list(complex_job.keys())}")
    
    try:
        result = await airtable.add_jobs([complex_job])
        print("✅ Complex test passed")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Complex test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_airtable_debug())
