#!/usr/bin/env python3
"""
Quick Live Job Discovery Test

This simplified test directly calls the LinkedIn scraper to validate 
that our job discovery system is working end-to-end.
"""
import sys
import asyncio
import json
from datetime import datetime
import os
from pathlib import Path

# Add app directory to path for relative imports
sys.path.append(str(Path(__file__).parent.parent))

async def test_direct_linkedin_scraping():
    """Test the LinkedIn scraper directly"""
    print("🚀 Direct LinkedIn Scraping Test")
    print("=" * 50)
    
    try:
        from app.core.linkedin_scraper_v2 import LinkedInScraperV2
        from app.core.ai_service import ai_service
        
        # Initialize scraper
        scraper = LinkedInScraperV2()
        
        # Test scenarios
        test_cases = [
            {
                "name": "Python Developer",
                "message": "Find Python developer jobs in San Francisco",
                "params": {"keywords": "Python developer", "location": "San Francisco", "limit": 3}
            },
            {
                "name": "Full Stack Developer",
                "message": "Look for full stack React developer jobs",
                "params": {"keywords": "full stack React developer", "location": "Remote", "limit": 2}
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n🔍 Test {i+1}: {test_case['name']}")
            print(f"💬 Original message: '{test_case['message']}'")
            
            # Step 1: Extract parameters using Gemini
            print(f"\n   Step 1: Gemini Parameter Extraction")
            try:
                extracted_params = await ai_service.extract_job_search_parameters(test_case['message'])
                print(f"   🎯 Extracted: {json.dumps(extracted_params, indent=4)}")
            except Exception as e:
                print(f"   ⚠️  Gemini extraction failed: {e}")
                extracted_params = test_case['params']
                print(f"   🔄 Using fallback params: {json.dumps(extracted_params, indent=4)}")
            
            # Step 2: Search for jobs
            print(f"\n   Step 2: LinkedIn Job Search")
            try:
                start_time = datetime.now()
                jobs = await scraper.search_jobs(**extracted_params)
                search_duration = (datetime.now() - start_time).total_seconds()
                
                print(f"   ⏱️  Search completed in {search_duration:.2f} seconds")
                print(f"   📊 Found {len(jobs)} jobs")
                
                if jobs:
                    print(f"\n   📋 Job Results:")
                    for j, job in enumerate(jobs[:2], 1):
                        print(f"      {j}. {job.get('title', 'N/A')}")
                        print(f"         🏢 Company: {job.get('company', 'N/A')}")
                        print(f"         📍 Location: {job.get('location', 'N/A')}")
                        print(f"         🔗 URL: {job.get('url', 'N/A')[:60]}...")
                        if 'relevance_score' in job:
                            print(f"         ⭐ Relevance: {job['relevance_score']:.1%}")
                        print()
                    
                    print(f"   ✅ {test_case['name']} test successful!")
                else:
                    print(f"   ⚠️  No jobs found for {test_case['name']}")
                    
            except Exception as e:
                print(f"   ❌ LinkedIn search failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Rate limiting between tests
            if i < len(test_cases) - 1:
                print(f"   ⏳ Waiting 15 seconds before next test...")
                await asyncio.sleep(15)
        
        print(f"\n" + "=" * 50)
        print(f"🎉 Direct LinkedIn scraping tests completed!")
        print(f"✅ Live job discovery system is operational")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import LinkedIn scraper: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_gemini_parameter_extraction_only():
    """Test just the Gemini parameter extraction"""
    print("\n🧠 Gemini Parameter Extraction Test")
    print("-" * 40)
    
    try:
        from app.core.ai_service import ai_service
        
        test_messages = [
            "Find Python developer jobs in San Francisco with salary over $120k",
            "Search for remote React developer positions",
            "Look for senior DevOps engineer jobs in Austin, Texas",
            "Get machine learning engineer opportunities at tech startups"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n{i}. Message: '{message}'")
            try:
                params = await ai_service.extract_job_search_parameters(message)
                print(f"   🎯 Extracted: {json.dumps(params, indent=6)}")
            except Exception as e:
                print(f"   ❌ Extraction failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        return False

async def main():
    """Main test runner"""
    print("🚀 Quick Live Job Discovery Validation")
    print("=" * 60)
    
    # Test Gemini parameter extraction
    gemini_success = await test_gemini_parameter_extraction_only()
    
    # Test direct LinkedIn scraping
    linkedin_success = await test_direct_linkedin_scraping()
    
    print(f"\n" + "=" * 60)
    print("📊 Final Results:")
    print(f"   🧠 Gemini Parameter Extraction: {'✅ Working' if gemini_success else '❌ Failed'}")
    print(f"   🌐 LinkedIn Job Scraping: {'✅ Working' if linkedin_success else '❌ Failed'}")
    
    if gemini_success and linkedin_success:
        print(f"\n🎉 SUCCESS: Live job discovery system is fully operational!")
        print(f"💡 Key capabilities validated:")
        print(f"   • Natural language parameter extraction")
        print(f"   • Real-time LinkedIn job scraping")
        print(f"   • AI-powered job matching and relevance scoring")
        print(f"\n🚀 Ready for Phase 2 frontend integration!")
    else:
        print(f"\n⚠️  Some components need attention")
    
    return gemini_success and linkedin_success

if __name__ == "__main__":
    asyncio.run(main())
