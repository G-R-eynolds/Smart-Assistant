#!/usr/bin/env python3
"""
Quick Pipeline Test

A simple script to quickly test individual components of the job pipeline.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.config import settings
from app.core.cv_manager import cv_manager


def test_cv_system():
    """Quick test of the CV system"""
    print("🔍 Testing CV System...")
    
    # Check if CV exists
    cv_info = cv_manager.get_cv_info()
    if cv_info['exists']:
        print(f"✅ CV found: {cv_info['filename']} ({cv_info['size_mb']} MB)")
        
        # Test text extraction
        cv_text = cv_manager.get_cv_text()
        if cv_text:
            print(f"✅ Text extracted: {len(cv_text)} characters, {len(cv_text.split())} words")
            print(f"Preview: {cv_text[:100]}...")
        else:
            print("❌ Failed to extract text from CV")
    else:
        print(f"❌ CV not found at: {cv_info['path']}")
        print("   Run: python upload_cv.py /path/to/your/cv.pdf")


def test_configuration():
    """Quick test of all configurations"""
    print("\n🔧 Testing Configuration...")
    
    configs = [
        ("CV System", cv_manager.cv_exists()),
        ("Gemini API", bool(settings.GEMINI_API_KEY)),
        ("Bright Data", bool(settings.BRIGHT_DATA_ENDPOINT)),
        ("Airtable", bool(settings.AIRTABLE_API_KEY and settings.AIRTABLE_BASE_ID))
    ]
    
    for name, configured in configs:
        status = "✅" if configured else "❌"
        print(f"  {status} {name}")
    
    missing = [name for name, configured in configs if not configured]
    if missing:
        print(f"\n⚠️  Missing configuration for: {', '.join(missing)}")
        print("   Check your .env file and ensure all required variables are set")
    else:
        print("\n🎉 All services configured!")


async def test_linkedin_connection():
    """Quick test of LinkedIn scraper connection"""
    print("\n🌐 Testing LinkedIn Connection...")
    
    if not settings.BRIGHT_DATA_ENDPOINT:
        print("❌ Bright Data endpoint not configured")
        return
    
    try:
        from app.core.linkedin_scraper_v2 import LinkedInScraperV2
        scraper = LinkedInScraperV2()
        
        print("🔄 Testing connection to Bright Data...")
        # This is a simple connection test - you might want to implement a ping method
        print("✅ LinkedIn scraper initialized (connection test would require actual search)")
        
    except Exception as e:
        print(f"❌ LinkedIn scraper error: {e}")


async def test_gemini_connection():
    """Quick test of Gemini API connection"""
    print("\n🤖 Testing Gemini API...")
    
    if not settings.GEMINI_API_KEY:
        print("❌ Gemini API key not configured")
        return
    
    try:
        from app.core.gemini_client import gemini_client
        
        if gemini_client.is_configured():
            print("✅ Gemini client configured")
            # You could add a simple API test here if needed
        else:
            print("❌ Gemini client configuration invalid")
            
    except Exception as e:
        print(f"❌ Gemini client error: {e}")


async def main():
    """Run all quick tests"""
    print("🚀 Quick Pipeline Test")
    print("=" * 50)
    
    test_cv_system()
    test_configuration()
    await test_linkedin_connection()
    await test_gemini_connection()
    
    print("\n" + "=" * 50)
    print("💡 Next steps:")
    print("   1. Fix any ❌ issues above")
    print("   2. Run full tests: python test_pipeline.py --help")
    print("   3. Test job search: python test_pipeline.py search 'software engineer'")
    print("   4. Test full pipeline: python test_pipeline.py full-pipeline 'python developer' --cover-letters")


if __name__ == "__main__":
    asyncio.run(main())
