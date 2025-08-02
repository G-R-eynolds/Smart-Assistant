#!/usr/bin/env python3
"""
Live Job Discovery Test Script

This script tests the actual job discovery functionality with:
- Bright Data LinkedIn scraping
- Gemini API parameter extraction
- Smart Assistant pipeline integration
- Real job search scenarios
"""
import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp
import requests
from dotenv import load_dotenv
from pathlib import Path

# Find the project root directory and load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

class LiveJobDiscoveryTester:
    """Test class for live job discovery functionality"""
    
    def __init__(self):
        self.microservice_url = "http://localhost:8001"
        
        # Set up path for imports
        # The app package is now directly importable since we added the parent dir to path
        
        # Test scenarios
        self.test_scenarios = [
            {
                "name": "Python Developer - San Francisco",
                "user_message": "Find Python developer jobs in San Francisco with salary over $150k",
                "expected_params": {
                    "keywords": "Python developer",
                    "location": "San Francisco",
                    "salary_min": 150000
                }
            },
            {
                "name": "Machine Learning Engineer - Remote",
                "user_message": "Search for remote machine learning engineer positions at tech companies",
                "expected_params": {
                    "keywords": "machine learning engineer",
                    "location": "remote",
                    "company_type": "tech"
                }
            },
            {
                "name": "Full Stack Developer - New York",
                "user_message": "Look for full stack developer jobs in NYC, preferably React and Node.js",
                "expected_params": {
                    "keywords": "full stack developer React Node.js",
                    "location": "New York"
                }
            },
            {
                "name": "DevOps Engineer - Austin",
                "user_message": "Find DevOps engineer opportunities in Austin, Texas with Kubernetes experience",
                "expected_params": {
                    "keywords": "DevOps engineer Kubernetes",
                    "location": "Austin, Texas"
                }
            }
        ]
    
    async def test_gemini_parameter_extraction(self):
        """Test Gemini API parameter extraction functionality"""
        print("\n🧠 Testing Gemini API Parameter Extraction...")
        
        try:
            # Import Gemini service
            from app.core.ai_service import ai_service
            
            success_count = 0
            total_tests = len(self.test_scenarios)
            
            for scenario in self.test_scenarios:
                print(f"\n   🔍 Testing: {scenario['name']}")
                print(f"   📝 User message: '{scenario['user_message']}'")
                
                try:
                    # Extract parameters using Gemini
                    extracted_params = await ai_service.extract_job_search_parameters(
                        scenario['user_message']
                    )
                    
                    print(f"   🎯 Extracted parameters: {json.dumps(extracted_params, indent=2)}")
                    
                    # Validate extraction quality
                    expected = scenario['expected_params']
                    quality_score = self._evaluate_extraction_quality(extracted_params, expected)
                    
                    if quality_score >= 0.7:  # 70% accuracy threshold
                        print(f"   ✅ Parameter extraction successful (Quality: {quality_score:.1%})")
                        success_count += 1
                    else:
                        print(f"   ⚠️  Parameter extraction needs improvement (Quality: {quality_score:.1%})")
                
                except Exception as e:
                    print(f"   ❌ Parameter extraction failed: {e}")
                
                await asyncio.sleep(1)  # Rate limiting
            
            success_rate = success_count / total_tests
            print(f"\n   📊 Gemini Extraction Success Rate: {success_rate:.1%} ({success_count}/{total_tests})")
            return success_rate >= 0.8
            
        except ImportError as e:
            print(f"   ❌ Cannot import Gemini service: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Gemini test failed: {e}")
            return False
    
    def _evaluate_extraction_quality(self, extracted: Dict, expected: Dict) -> float:
        """Evaluate the quality of parameter extraction"""
        if not extracted:
            return 0.0
        
        score = 0.0
        total_checks = 0
        
        # Check if keywords are properly extracted
        if 'keywords' in expected:
            total_checks += 1
            extracted_keywords = extracted.get('keywords', '').lower()
            expected_keywords = expected['keywords'].lower()
            
            # Simple keyword matching
            keywords_found = sum(1 for word in expected_keywords.split() 
                               if word in extracted_keywords)
            keyword_score = keywords_found / len(expected_keywords.split())
            score += keyword_score
        
        # Check location extraction
        if 'location' in expected:
            total_checks += 1
            extracted_location = extracted.get('location', '').lower()
            expected_location = expected['location'].lower()
            
            if expected_location in extracted_location:
                score += 1.0
            elif any(word in extracted_location for word in expected_location.split()):
                score += 0.5
        
        # Check salary extraction
        if 'salary_min' in expected:
            total_checks += 1
            extracted_salary = extracted.get('salary_min', 0)
            expected_salary = expected['salary_min']
            
            if extracted_salary >= expected_salary * 0.8:  # Within 20%
                score += 1.0
        
        return score / total_checks if total_checks > 0 else 0.0
    
    async def test_bright_data_integration(self):
        """Test Bright Data LinkedIn scraping integration"""
        print("\n🌐 Testing Bright Data LinkedIn Integration...")
        
        try:
            # Import LinkedIn scraper
            from app.core.linkedin_scraper_v2 import LinkedInScraperV2
            
            scraper = LinkedInScraperV2()
            
            # Test with a simple search
            test_params = {
                "keywords": "Python developer",
                "location": "San Francisco",
                "limit": 3  # Small limit for testing
            }
            
            print(f"   🔍 Testing search with parameters: {json.dumps(test_params, indent=2)}")
            
            start_time = time.time()
            jobs = await scraper.search_jobs(**test_params)
            search_duration = time.time() - start_time
            
            print(f"   ⏱️  Search completed in {search_duration:.2f} seconds")
            print(f"   📊 Found {len(jobs)} jobs")
            
            if jobs:
                # Display first job for validation
                first_job = jobs[0]
                print(f"   📋 Sample job:")
                print(f"      • Title: {first_job.get('title', 'N/A')}")
                print(f"      • Company: {first_job.get('company', 'N/A')}")
                print(f"      • Location: {first_job.get('location', 'N/A')}")
                print(f"      • URL: {first_job.get('url', 'N/A')[:80]}...")
                
                print(f"   ✅ Bright Data integration working correctly")
                return True
            else:
                print(f"   ⚠️  No jobs found - may indicate rate limiting or search issues")
                return False
                
        except ImportError as e:
            print(f"   ❌ Cannot import LinkedIn scraper: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Bright Data test failed: {e}")
            return False
    
    async def test_end_to_end_job_discovery(self):
        """Test complete end-to-end job discovery pipeline"""
        print("\n🔄 Testing End-to-End Job Discovery Pipeline...")
        
        try:
            success_count = 0
            total_tests = min(2, len(self.test_scenarios))  # Limit for API rate limits
            
            for i, scenario in enumerate(self.test_scenarios[:total_tests]):
                print(f"\n   🚀 E2E Test {i+1}: {scenario['name']}")
                print(f"   💬 User message: '{scenario['user_message']}'")
                
                try:
                    # Step 1: Test microservice endpoint
                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "search_params": {"query": scenario['user_message']},
                            "max_results": 3,
                            "force_refresh": True
                        }
                        
                        start_time = time.time()
                        async with session.post(
                            f"{self.microservice_url}/api/v1/jobs/discover",
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            response_time = time.time() - start_time
                            
                            if response.status == 200:
                                result = await response.json()
                                
                                print(f"   ✅ Microservice responded in {response_time:.2f}s")
                                print(f"   📊 Status: {result.get('status', 'unknown')}")
                                print(f"   🎯 Jobs found: {result.get('jobs_found', 0)}")
                                print(f"   💾 Jobs saved: {result.get('jobs_saved', 0)}")
                                print(f"   ⭐ Qualified jobs: {result.get('qualified_jobs', 0)}")
                                
                                # Display sample jobs if available
                                jobs = result.get('jobs', [])
                                if jobs:
                                    print(f"   📋 Sample jobs:")
                                    for j, job in enumerate(jobs[:2]):
                                        print(f"      {j+1}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
                                
                                if result.get('jobs_found', 0) > 0:
                                    success_count += 1
                                    print(f"   🎉 E2E test successful!")
                                else:
                                    print(f"   ⚠️  No jobs found in E2E test")
                            else:
                                print(f"   ❌ Microservice error: {response.status}")
                                error_text = await response.text()
                                print(f"      Error details: {error_text[:200]}")
                
                except Exception as e:
                    print(f"   ❌ E2E test failed: {e}")
                
                # Rate limiting between tests
                if i < total_tests - 1:
                    print(f"   ⏳ Waiting 10 seconds before next test...")
                    await asyncio.sleep(10)
            
            success_rate = success_count / total_tests
            print(f"\n   📊 E2E Success Rate: {success_rate:.1%} ({success_count}/{total_tests})")
            return success_rate >= 0.5  # 50% success rate for E2E
            
        except Exception as e:
            print(f"   ❌ E2E pipeline test failed: {e}")
            return False
    
    async def test_pipeline_function_integration(self):
        """Test the pipeline function directly"""
        print("\n🔗 Testing Pipeline Function Integration...")
        
        try:
            # Import our pipeline function from app
            from app.functions import job_discovery
            
            # Create pipeline instance
            pipeline = job_discovery.Pipeline()
            
            print(f"   ✅ Pipeline loaded: {pipeline.name}")
            print(f"   🆔 Pipeline ID: {pipeline.id}")
            print(f"   ⚙️  Enabled: {pipeline.valves.enabled}")
            
            # Test with a job search message
            test_message = {
                "role": "user",
                "content": "Find Python developer jobs in San Francisco"
            }
            
            test_user = {
                "id": "test_user_123",
                "email": "test@example.com"
            }
            
            print(f"   🧪 Testing message: '{test_message['content']}'")
            
            # Test inlet method
            test_body = {
                "messages": [test_message]
            }
            
            result = await pipeline.inlet(test_body, test_user)
            
            if result != test_body:
                print(f"   ✅ Pipeline processed message successfully")
                if isinstance(result, dict) and 'messages' in result:
                    # Check if new messages were added or modified
                    if len(result['messages']) > len(test_body['messages']):
                        print(f"   📄 Pipeline added response messages")
                        
                        # Check the last message content
                        last_message = result['messages'][-1]
                        content = last_message.get('content', '')
                        content_length = len(content)
                        print(f"   📄 Response length: {content_length} characters")
                        
                        # Check if response contains job-related content
                        content_lower = content.lower()
                        job_indicators = ['job', 'position', 'developer', 'company', 'salary']
                        found_indicators = sum(1 for indicator in job_indicators if indicator in content_lower)
                        
                        if found_indicators >= 2:
                            print(f"   🎯 Response contains relevant job content")
                            return True
                        else:
                            print(f"   ⚠️  Response may not contain job content")
                            return False
                    else:
                        print(f"   ⚠️  No new messages added by pipeline")
                        return False
                else:
                    print(f"   ⚠️  Unexpected response format")
                    return False
            else:
                print(f"   ⚠️  Pipeline did not process the message")
                return False
                
        except Exception as e:
            print(f"   ❌ Pipeline function test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_environment_setup(self):
        """Test that all required environment variables and services are configured"""
        print("\n🔧 Testing Environment Setup...")
        
        required_env_vars = [
            'GEMINI_API_KEY',
            'BRIGHT_DATA_USERNAME', 
            'BRIGHT_DATA_PASSWORD',
            'AIRTABLE_API_KEY',
            'AIRTABLE_BASE_ID'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
            else:
                print(f"   ✅ {var} configured")
        
        if missing_vars:
            print(f"   ⚠️  Missing environment variables: {', '.join(missing_vars)}")
            print(f"      These may be required for full functionality")
        
        # Test microservice availability
        try:
            response = requests.get(f"{self.microservice_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ Microservice health: {health_data.get('status', 'unknown')}")
                print(f"   🔗 Smart Assistant available: {health_data.get('smart_assistant_available', False)}")
            else:
                print(f"   ⚠️  Microservice health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Microservice not accessible: {e}")
            return False
        
        return len(missing_vars) <= 1  # Allow one missing var
    
    async def run_all_tests(self):
        """Run comprehensive live job discovery tests"""
        print("🚀 Live Job Discovery Test Suite")
        print("=" * 60)
        
        results = []
        
        # Test environment setup
        results.append(self.test_environment_setup())
        
        # Test Gemini parameter extraction
        results.append(await self.test_gemini_parameter_extraction())
        
        # Test Bright Data integration
        results.append(await self.test_bright_data_integration())
        
        # Test pipeline function integration
        results.append(await self.test_pipeline_function_integration())
        
        # Test end-to-end pipeline
        results.append(await self.test_end_to_end_job_discovery())
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Live Job Discovery Test Results:")
        print(f"   ✅ Passed: {sum(results)}")
        print(f"   ❌ Failed: {len(results) - sum(results)}")
        
        if all(results):
            print("\n🎉 All Live Job Discovery Tests Passed!")
            print("🚀 System is ready for production job discovery!")
        else:
            print("\n⚠️  Some tests failed - review configuration and setup")
            
            # Provide specific recommendations
            test_names = [
                "Environment Setup",
                "Gemini Parameter Extraction", 
                "Bright Data Integration",
                "Pipeline Function Integration",
                "End-to-End Discovery"
            ]
            
            for i, (test_name, passed) in enumerate(zip(test_names, results)):
                if not passed:
                    print(f"   🔧 Fix needed: {test_name}")
        
        return all(results)

async def main():
    """Main test execution"""
    tester = LiveJobDiscoveryTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 Next Steps:")
        print("   • Deploy to production environment")
        print("   • Configure monitoring and alerting")
        print("   • Set up user feedback collection")
        print("   • Proceed with Phase 2 frontend integration")
    else:
        print("\n🔧 Recommended Actions:")
        print("   • Check environment variables configuration")
        print("   • Verify Bright Data and Gemini API credentials")
        print("   • Ensure microservice is running correctly")
        print("   • Review logs for detailed error information")
    
    return success

if __name__ == "__main__":
    import importlib.util
    asyncio.run(main())
