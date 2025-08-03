#!/usr/bin/env python3
"""
Complete Job Pipeline Test with Relevance Scoring

Tests the full pipeline: Search → AI Analysis → Relevance Filtering → Cover Letters → Airtable
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.linkedin_scraper_v2 import LinkedInScraperV2
from app.core.gemini_client import gemini_client
from app.core.airtable_client import airtable_client
from app.core.cv_manager import cv_manager
from app.core.job_deduplication import job_deduplication_service
from app.core.database import init_db, close_db


async def test_complete_pipeline():
    """Test the complete job pipeline with AI relevance scoring"""
    
    # Initialize database
    await init_db()
    
    print("🚀 Starting Complete Job Pipeline Test")
    print("=" * 60)
    
    # Configuration
    query = "I want remote Python developer jobs"
    max_results = 3
    min_relevance_score = 0.7
    
    # Initialize
    scraper = LinkedInScraperV2()
    
    # Step 1: Check prerequisites
    print("1️⃣ Checking Prerequisites...")
    print(f"   Gemini API: {'✅' if gemini_client.is_configured() else '❌'}")
    print(f"   CV Available: {'✅' if cv_manager.cv_exists() else '❌'}")
    print(f"   Airtable: {'✅' if airtable_client.is_configured() else '❌'}")
    
    if not gemini_client.is_configured():
        print("❌ Cannot proceed without Gemini API")
        return
    
    # Step 2: AI Keyword Extraction
    print(f"\n2️⃣ AI Keyword Extraction: '{query}'")
    keywords_result = await gemini_client.extract_job_search_keywords(query)
    
    if keywords_result.get("success"):
        keywords = keywords_result.get("keywords", query)
        location = keywords_result.get("location", "")
        print(f"   ✅ Keywords: '{keywords}'")
        print(f"   📍 Location: '{location}'")
    else:
        keywords = query
        location = ""
        print(f"   ⚠️ Using original query")
    
    # Step 3: LinkedIn Search  
    print(f"\n3️⃣ LinkedIn Job Search...")
    jobs = await scraper.search_jobs(keywords=keywords, location=location, limit=max_results)
    
    print(f"   Found {len(jobs)} jobs")
    for i, job in enumerate(jobs, 1):
        print(f"   {i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
    
    if not jobs:
        print("❌ No jobs found - stopping")
        await close_db()
        return
    
    # Step 3.5: Deduplication Check
    print(f"\n🔍 Checking for Duplicate Jobs...")
    new_jobs = await job_deduplication_service.process_jobs_with_deduplication(jobs)
    
    if not new_jobs:
        print("   ⚠️ All jobs were duplicates - stopping")
        await close_db()
        return
    elif len(new_jobs) < len(jobs):
        print(f"   📊 Filtered out {len(jobs) - len(new_jobs)} duplicates, {len(new_jobs)} new jobs to process")
    else:
        print(f"   ✅ All {len(new_jobs)} jobs are new")

    # Step 4: AI Analysis & Relevance Scoring
    print(f"\n4️⃣ AI Analysis & Relevance Scoring (threshold: {min_relevance_score})")
    
    high_relevance_jobs = []
    
    for i, job in enumerate(new_jobs, 1):
        print(f"\n   Analyzing Job {i}: {job.get('title', 'N/A')}")
        
        try:
            # Get job analysis with relevance score
            analysis_result = await gemini_client.analyze_job_posting(job.get("description", ""))
            
            if analysis_result.get("success") and "analysis" in analysis_result:
                analysis = analysis_result["analysis"]
                relevance_score = analysis.get("relevance_score", 0.0)
                
                print(f"   🎯 Relevance: {relevance_score:.2f}")
                print(f"   💭 Reasoning: {analysis.get('match_reasoning', 'N/A')[:80]}...")
                
                # Add analysis to job
                job["relevance_score"] = relevance_score
                job["job_analysis"] = analysis_result
                
                if relevance_score >= min_relevance_score:
                    print(f"   ✅ PASSES filter ({relevance_score:.2f} >= {min_relevance_score})")
                    high_relevance_jobs.append(job)
                else:
                    print(f"   ❌ Filtered out ({relevance_score:.2f} < {min_relevance_score})")
            else:
                print(f"   ⚠️ Analysis failed")
                job["relevance_score"] = 0.0
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            job["relevance_score"] = 0.0
    
    print(f"\n   📊 Results: {len(high_relevance_jobs)}/{len(jobs)} jobs passed relevance filter")
    
    # Step 5: Generate Cover Letters
    if high_relevance_jobs:
        print(f"\n5️⃣ Generating Cover Letters...")
        
        for i, job in enumerate(high_relevance_jobs, 1):
            print(f"   Generating {i}/{len(high_relevance_jobs)}: {job.get('title', 'N/A')}")
            
            try:
                cover_letter_result = await gemini_client.generate_cover_letter(
                    job_title=job.get("title", ""),
                    company=job.get("company", ""),
                    job_description=job.get("description", "")
                )
                
                job["cover_letter"] = cover_letter_result
                
                if cover_letter_result.get("success"):
                    letter_length = len(cover_letter_result.get("cover_letter", ""))
                    print(f"   ✅ Generated ({letter_length} characters)")
                else:
                    print(f"   ❌ Failed: {cover_letter_result.get('error', 'Unknown')}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    # Step 6: Save to Airtable
    if high_relevance_jobs and airtable_client.is_configured():
        print(f"\n6️⃣ Saving to Airtable...")
        
        try:
            result = await airtable_client.add_jobs(high_relevance_jobs)
            
            if result.get("success"):
                records_created = result.get("count", 0)
                print(f"   ✅ Saved {records_created} jobs to Airtable")
                
                # Mark jobs as processed to avoid duplicates in future runs
                await job_deduplication_service.mark_jobs_as_processed(high_relevance_jobs)
                print(f"   📝 Marked {len(high_relevance_jobs)} jobs as processed")
            else:
                print(f"   ❌ Save failed: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    elif high_relevance_jobs:
        print(f"\n6️⃣ Airtable not configured - skipping save")
        # Still mark jobs as processed even if not saving to Airtable
        await job_deduplication_service.mark_jobs_as_processed(new_jobs)
        print(f"   📝 Marked {len(new_jobs)} analyzed jobs as processed")
    else:
        print(f"\n6️⃣ No jobs to save")
        # Mark all analyzed jobs as processed to avoid re-analyzing
        await job_deduplication_service.mark_jobs_as_processed(new_jobs)
        print(f"   📝 Marked {len(new_jobs)} analyzed jobs as processed")
    
    # Final Summary
    print(f"\n🎉 Pipeline Complete!")
    print("=" * 60)
    print(f"Query: '{query}'")
    print(f"Jobs found: {len(jobs)}")
    print(f"New jobs: {len(new_jobs)}")
    print(f"High relevance: {len(high_relevance_jobs)}")
    
    cover_letters = sum(1 for job in high_relevance_jobs if job.get('cover_letter', {}).get('success'))
    print(f"Cover letters: {cover_letters}")
    
    saved = len(high_relevance_jobs) > 0 and airtable_client.is_configured()
    print(f"Saved to Airtable: {saved}")
    print("=" * 60)
    
    # Cleanup
    await close_db()


if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())
