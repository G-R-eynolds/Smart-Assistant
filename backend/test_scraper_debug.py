#!/usr/bin/env python3
"""
Debug script to test the LinkedIn scraper and see what's happening
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.linkedin_scraper_v2 import LinkedInScraperV2

async def test_scraper():
    print("🧪 Testing LinkedIn Scraper Debug")
    print("=" * 50)
    
    scraper = LinkedInScraperV2()
    
    # Test with a simple search
    keywords = "python developer"
    location = "remote"
    
    print(f"🔍 Testing search: '{keywords}' in '{location}'")
    print(f"🌐 Bright Data endpoint configured: {scraper.websocket_endpoint is not None}")
    
    if scraper.websocket_endpoint:
        print(f"📡 Endpoint: {scraper.websocket_endpoint[:50]}..." if len(scraper.websocket_endpoint) > 50 else scraper.websocket_endpoint)
    else:
        print("❌ No Bright Data endpoint configured!")
        return
    
    try:
        print("\n🚀 Starting search...")
        jobs = await scraper.search_jobs(
            keywords=keywords,
            location=location,
            limit=3
        )
        
        print(f"\n✅ Search completed!")
        print(f"📊 Found {len(jobs)} jobs")
        
        if jobs:
            print("\n📋 Jobs found:")
            for i, job in enumerate(jobs, 1):
                print(f"  {i}. {job.get('title', 'No title')} at {job.get('company', 'No company')}")
                print(f"     📍 {job.get('location', 'No location')}")
                print(f"     🔗 {job.get('url', 'No URL')}")
                print()
        else:
            print("\n❌ No jobs found - this indicates a scraping issue")
            
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await scraper.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_scraper())
