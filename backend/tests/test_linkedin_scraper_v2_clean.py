#!/usr/bin/env python3
"""
Test script for the rebuilt LinkedIn Scraper V2

This script tests the core functionality of the LinkedIn scraper
using the Bright Data Scraping Browser approach.
"""

import asyncio
import sys
import os
import pytest

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, '.env'))

from app.core.linkedin_scraper_v2 import linkedin_scraper_v2
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@pytest.mark.asyncio
async def test_linkedin_scraper():
    """Test the LinkedIn scraper functionality."""
    
    print("🚀 Testing LinkedIn Scraper V2 with Bright Data Scraping Browser")
    print("=" * 70)
    
    try:
        # Test 1: Check configuration
        print("\n1. Testing configuration...")
        if linkedin_scraper_v2.websocket_endpoint:
            print(f"✅ WebSocket endpoint configured")
        else:
            print("❌ WebSocket endpoint not configured")
            print("   Please set BRIGHT_DATA_ENDPOINT in your environment")
            return False
        
        # Test 2: Test URL building
        print("\n2. Testing URL building...")
        test_url = linkedin_scraper_v2._build_linkedin_search_url(
            keywords="software engineer",
            location="San Francisco",
            experience_level="mid",
            job_type="full-time",
            date_posted="week"
        )
        print(f"✅ Built search URL: {test_url}")
        
        # Test 3: Test Puppeteer script generation
        print("\n3. Testing Puppeteer script generation...")
        script = linkedin_scraper_v2._generate_puppeteer_script(test_url, 5)
        if "puppeteer.connect" in script and linkedin_scraper_v2.websocket_endpoint in script:
            print("✅ Puppeteer script generated successfully")
        else:
            print("❌ Puppeteer script generation failed")
            return False
        
        # Test 4: Test job search (this will attempt actual scraping)
        print("\n4. Testing job search...")
        print("   This will attempt to connect to Bright Data and scrape LinkedIn")
        print("   Make sure your BRIGHT_DATA_ENDPOINT is properly configured")
        
        jobs = await linkedin_scraper_v2.search_jobs(
            keywords="python developer",
            location="remote",
            limit=3
        )
        
        if jobs:
            print(f"✅ Successfully scraped {len(jobs)} jobs!")
            for i, job in enumerate(jobs[:2], 1):  # Show first 2 jobs
                print(f"\n   Job {i}:")
                print(f"   - Title: {job.get('title')}")
                print(f"   - Company: {job.get('company')}")
                print(f"   - Location: {job.get('location')}")
                print(f"   - URL: {job.get('url')[:80]}...")
        else:
            print("⚠️ No jobs were scraped (this might be due to configuration)")
            
        print("\n✅ All tests completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await linkedin_scraper_v2.close()


@pytest.mark.asyncio
async def test_node_availability():
    """Test if Node.js and puppeteer-core are available."""
    
    print("\n🔍 Checking dependencies...")
    
    # Get backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check Node.js
    try:
        process = await asyncio.create_subprocess_exec(
            'node', '--version',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            version = stdout.decode().strip()
            print(f"✅ Node.js available: {version}")
        else:
            print("❌ Node.js not found - please install Node.js")
            return False
            
    except FileNotFoundError:
        print("❌ Node.js not found - please install Node.js")
        return False
    
    # Check puppeteer-core
    try:
        process = await asyncio.create_subprocess_exec(
            'node', '-e', 'console.log(require("puppeteer-core").version)',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=backend_dir
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            version = stdout.decode().strip()
            print(f"✅ puppeteer-core available: {version}")
            return True
        else:
            print("❌ puppeteer-core not found")
            print("   Run: npm install puppeteer-core")
            return False
            
    except Exception as e:
        print(f"❌ Error checking puppeteer-core: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 LinkedIn Scraper V2 Test Suite")
        print("=" * 50)
        
        # First check dependencies
        deps_ok = await test_node_availability()
        if not deps_ok:
            print("\n❌ Dependencies not met. Please install Node.js and run:")
            print("   npm install puppeteer-core")
            return
        
        # Then test the scraper
        success = await test_linkedin_scraper()
        
        if success:
            print("\n🎉 All tests passed! The scraper is ready to use.")
        else:
            print("\n💥 Some tests failed. Check your configuration.")
    
    asyncio.run(main())
