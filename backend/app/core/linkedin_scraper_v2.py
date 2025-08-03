"""
LinkedIn Job Scraper using Bright Data Scraping Browser

A production-ready LinkedIn job scraper that integrates with Bright Data's
Scraping Browser service using Puppeteer-over-WebSocket connections.
Based on the official Bright Data implementation patterns.

Reference: https://github.com/luminati-io/bright-data-scraping-browser-nodejs-puppeteer-project
"""

import asyncio
import json
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from urllib.parse import urlencode
import re

from app.core.config import settings

logger = structlog.get_logger()


class LinkedInScraperV2:
    """
    LinkedIn job scraper using Bright Data's Scraping Browser with Puppeteer.
    
    This implementation follows the official Bright Data patterns for
    browser automation via WebSocket connections, using Node.js + Puppeteer
    execution through subprocess calls.
    """
    
    def __init__(self):
        self.websocket_endpoint = self._build_websocket_endpoint()
        self.rate_limit_delay = 2.0
        self.last_request_time = None
        
    def _build_websocket_endpoint(self) -> Optional[str]:
        """Build the Bright Data Scraping Browser WebSocket endpoint."""
        if not settings.BRIGHT_DATA_ENDPOINT:
            logger.warning("Bright Data WebSocket endpoint not configured")
            return None
            
        # The endpoint should be in WebSocket format:
        # wss://brd-customer-[id]-zone-[zone]:[password]@[domain]:[port]
        return settings.BRIGHT_DATA_ENDPOINT
    
    async def search_jobs(
        self,
        keywords: str,
        location: str = "",
        experience_level: str = "",
        job_type: str = "",
        date_posted: str = "week",
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn using Bright Data Scraping Browser.
        """
        if not self.websocket_endpoint:
            raise Exception("Bright Data Scraping Browser is not configured")
        
        await self._rate_limit()
        
        try:
            logger.info("Starting LinkedIn job search", 
                       keywords=keywords, location=location, limit=limit)
            
            search_url = self._build_linkedin_search_url(
                keywords, location, experience_level, job_type, date_posted
            )
            
            jobs = await self._scrape_with_puppeteer(search_url, limit)
            
            validated_jobs = self._validate_and_clean_jobs(jobs)
            
            # Enhance jobs with full descriptions by visiting individual job URLs
            if validated_jobs:
                logger.info("Enhancing jobs with full descriptions from individual job pages")
                validated_jobs = await self.enhance_jobs_with_full_descriptions(validated_jobs)
            
            logger.info(f"Successfully scraped {len(validated_jobs)} jobs from LinkedIn")
            return validated_jobs
            
        except Exception as e:
            logger.error("LinkedIn job search failed", error=str(e), exc_info=True)
            raise e

    async def _scrape_with_puppeteer(self, search_url: str, limit: int) -> List[Dict[str, Any]]:
        """
        Use Bright Data's Scraping Browser with Puppeteer to scrape LinkedIn jobs.
        """
        try:
            # Generate the Puppeteer script
            script_content = self._generate_puppeteer_script(search_url, limit)
            
            # Execute the script using Node.js
            jobs = await self._execute_nodejs_script(script_content)
            
            return jobs if jobs else []
            
        except Exception as e:
            logger.error(f"Puppeteer scraping failed: {e}")
            return []

    async def _execute_nodejs_script(self, script_content: str) -> List[Dict[str, Any]]:
        """
        Execute the Puppeteer script using Node.js subprocess.
        """
        try:
            # Get the backend directory where node_modules is located
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Create a temporary file for the script in the backend directory
            temp_file_path = os.path.join(backend_dir, f"temp_scraper_{os.getpid()}.js")
            
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write(script_content)
            
            logger.info("Executing Puppeteer script via Node.js")
            
            # Execute the Node.js script from the backend directory
            process = await asyncio.create_subprocess_exec(
                'node', temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=backend_dir
            )
            
            stdout, stderr = await process.communicate()
            
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass  # File might already be deleted
            
            if process.returncode == 0:
                try:
                    # Parse the JSON output
                    result = json.loads(stdout.decode())
                    if isinstance(result, list):
                        logger.info(f"Successfully extracted {len(result)} jobs via Puppeteer")
                        return result
                    else:
                        logger.warning("Unexpected result format from Puppeteer script")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Puppeteer output: {e}")
                    logger.error(f"Raw output: {stdout.decode()}")
                    return []
            else:
                logger.error(f"Puppeteer script failed with return code {process.returncode}")
                logger.error(f"Error output: {stderr.decode()}")
                return []
                
        except FileNotFoundError:
            logger.error("Node.js not found. Please install Node.js to use Puppeteer scraping")
            return []
        except Exception as e:
            logger.error(f"Error executing Node.js script: {e}")
            return []
    
    async def enhance_jobs_with_full_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance jobs with full descriptions by visiting individual job URLs.
        """
        if not jobs:
            return jobs
        
        logger.info(f"Enhancing {len(jobs)} jobs with full descriptions")
        enhanced_jobs = []
        
        for i, job in enumerate(jobs, 1):
            job_url = job.get('url', '')
            if not job_url:
                logger.warning(f"Job {i} has no URL, skipping description enhancement")
                enhanced_jobs.append(job)
                continue
            
            logger.info(f"Fetching full description for job {i}/{len(jobs)}: {job.get('title', 'Unknown')}")
            logger.info(f"Job URL: {job_url}")
            
            try:
                # Rate limiting between requests
                await self._rate_limit()
                
                # Get full description from job page
                full_description = await self._scrape_job_description(job_url)
                
                if full_description and len(full_description.strip()) > 50:
                    job['description'] = full_description
                    job['description_source'] = 'full_page'
                    logger.info(f"✅ Enhanced job with full description ({len(full_description)} chars)")
                else:
                    job['description_source'] = 'search_page'
                    logger.warning(f"⚠️ Could not get substantial full description for job {i} (got {len(full_description) if full_description else 0} chars)")
                
            except Exception as e:
                logger.error(f"❌ Failed to enhance job {i} with full description: {e}")
                job['description_source'] = 'search_page'
            
            enhanced_jobs.append(job)
        
        return enhanced_jobs
    
    async def _scrape_job_description(self, job_url: str) -> Optional[str]:
        """
        Scrape the full job description from a LinkedIn job page.
        """
        try:
            logger.info(f"🔍 Generating Puppeteer script for: {job_url}")
            script_content = self._generate_job_description_script(job_url)
            
            logger.info(f"🚀 Executing Puppeteer script...")
            result = await self._execute_nodejs_script(script_content)
            
            if result and len(result) > 0:
                if 'description' in result[0]:
                    description = result[0]['description']
                    if description and len(description.strip()) > 50:
                        logger.info(f"✅ Successfully scraped description ({len(description)} chars)")
                        return description
                    else:
                        logger.warning(f"⚠️ Description too short: {len(description) if description else 0} chars")
                        return None
                else:
                    logger.warning(f"⚠️ No 'description' field in result: {list(result[0].keys()) if result[0] else 'empty result'}")
                    return None
            else:
                logger.warning(f"⚠️ Empty or no result from Puppeteer script")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error scraping job description from {job_url}: {e}")
            return None
    
    def _generate_job_description_script(self, job_url: str) -> str:
        """
        Generate a Puppeteer script to scrape job description from individual job page.
        """
        return f"""
const puppeteer = require('puppeteer-core');

async function scrapeJobDescription() {{
    console.error('🚀 Starting job description scraper for: {job_url}');
    
    let browser;
    try {{
        // Connect to Bright Data's Scraping Browser
        console.error('🌐 Connecting to Bright Data Scraping Browser...');
        browser = await puppeteer.connect({{
            browserWSEndpoint: '{self.websocket_endpoint}'
        }});
        console.error('✅ Connected to browser');
        
        // Create a new page
        const page = await browser.newPage();
        
        // Set a realistic user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Navigate to job page
        console.error('🌐 Navigating to job page...');
        await page.goto('{job_url}', {{ 
            waitUntil: 'networkidle2', 
            timeout: 60000 
        }});
        console.error('✅ Job page loaded');
        
        // Wait for job description to appear
        console.error('⏳ Waiting for job description...');
        try {{
            await page.waitForSelector('.description__text, .show-more-less-html__markup, .jobs-box__html-content, .jobs-description__content', {{ 
                timeout: 30000 
            }});
            console.error('✅ Job description found');
        }} catch (e) {{
            console.error('⚠️ No job description found, proceeding anyway...');
        }}
        
        // Extract job description
        console.error('📊 Extracting job description...');
        const description = await page.evaluate(() => {{
            // Try multiple selectors for job description
            const descriptionSelectors = [
                '.description__text',
                '.show-more-less-html__markup',
                '.jobs-box__html-content', 
                '.jobs-description__content',
                '.jobs-description',
                '.job-description',
                '[data-testid="job-description"]'
            ];
            
            for (const selector of descriptionSelectors) {{
                const element = document.querySelector(selector);
                if (element) {{
                    // Get text content and clean it up
                    let text = element.textContent || element.innerText || '';
                    
                    // Clean up whitespace and formatting
                    text = text.replace(/\\s+/g, ' ').trim();
                    
                    if (text.length > 100) {{ // Make sure we got substantial content
                        console.log(`Found description with selector: ${{selector}} (${{text.length}} chars)`);
                        return text;
                    }}
                }}
            }}
            
            console.log('No substantial job description found');
            return '';
        }});
        
        console.error(`✅ Extracted description (${{description.length}} characters)`);
        
        // Output the result as JSON
        const result = [{{
            url: '{job_url}',
            description: description,
            scraped_at: new Date().toISOString()
        }}];
        
        console.log(JSON.stringify(result));
        
    }} catch (error) {{
        console.error('❌ Error occurred:', error.message);
        console.log(JSON.stringify([])); // Return empty array on error
    }} finally {{
        if (browser) {{
            await browser.close();
            console.error('👋 Browser closed');
        }}
    }}
}}

// Run the scraper
scrapeJobDescription();
"""

    def _generate_puppeteer_script(self, search_url: str, limit: int) -> str:
        """
        Generate a complete Puppeteer script for Node.js execution.
        Based on the official Bright Data implementation patterns.
        """
        return f"""
const puppeteer = require('puppeteer-core');

async function scrapeLinkedIn() {{
    console.error('🚀 Starting LinkedIn scraper...');
    
    let browser;
    try {{
        // Connect to Bright Data's Scraping Browser
        console.error('🌐 Connecting to Bright Data Scraping Browser...');
        browser = await puppeteer.connect({{
            browserWSEndpoint: '{self.websocket_endpoint}'
        }});
        console.error('✅ Connected to browser');
        
        // Create a new page
        const page = await browser.newPage();
        
        // Set a realistic user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Navigate to LinkedIn job search
        console.error('🌐 Navigating to LinkedIn...');
        await page.goto('{search_url}', {{ 
            waitUntil: 'networkidle2', 
            timeout: 60000 
        }});
        console.error('✅ Page loaded');
        
        // Wait for job cards to appear
        console.error('⏳ Waiting for job cards to load...');
        try {{
            await page.waitForSelector('.job-search-card, .base-card, [data-testid="job-card"]', {{ 
                timeout: 30000 
            }});
            console.error('✅ Job cards found');
        }} catch (e) {{
            console.error('⚠️ No job cards found, proceeding anyway...');
        }}
        
        // Scroll to load more jobs
        console.error('📜 Scrolling to load more jobs...');
        for (let i = 0; i < 3; i++) {{
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await new Promise(resolve => setTimeout(resolve, 2000));
        }}
        
        // Extract job data
        console.error('📊 Extracting job data...');
        const jobs = await page.evaluate((limit) => {{
            const jobCards = document.querySelectorAll(
                '.job-search-card, .base-card, [data-testid="job-card"], .base-search-card'
            );
            const results = [];
            
            console.log(`Found ${{jobCards.length}} job cards`);
            
            for (let i = 0; i < Math.min(jobCards.length, limit); i++) {{
                const card = jobCards[i];
                
                try {{
                    // Extract job details using multiple selectors
                    const titleSelectors = [
                        '.base-search-card__title',
                        '.job-search-card__title', 
                        '[data-testid="job-title"]',
                        '.base-card__title'
                    ];
                    
                    const companySelectors = [
                        '.base-search-card__subtitle',
                        '.job-search-card__subtitle',
                        '[data-testid="job-company"]',
                        '.base-card__subtitle'
                    ];
                    
                    const locationSelectors = [
                        '.job-search-card__location',
                        '[data-testid="job-location"]',
                        '.base-card__location'
                    ];
                    
                    const urlSelectors = [
                        '.base-card__full-link',
                        '.job-search-card__title-link',
                        '[data-testid="job-title-link"]'
                    ];
                    
                    const descriptionSelectors = [
                        '.job-search-card__snippet',
                        '.base-card__snippet',
                        '[data-testid="job-description"]'
                    ];
                    
                    const dateSelectors = [
                        'time',
                        '.job-search-card__listdate',
                        '[data-testid="job-posted-date"]'
                    ];
                    
                    // Helper function to get text from multiple selectors
                    const getTextFromSelectors = (selectors) => {{
                        for (const selector of selectors) {{
                            const element = card.querySelector(selector);
                            if (element) {{
                                return element.textContent?.trim() || '';
                            }}
                        }}
                        return '';
                    }};
                    
                    // Helper function to get href from multiple selectors
                    const getHrefFromSelectors = (selectors) => {{
                        for (const selector of selectors) {{
                            const element = card.querySelector(selector);
                            if (element && element.href) {{
                                return element.href;
                            }}
                        }}
                        return '';
                    }};
                    
                    const title = getTextFromSelectors(titleSelectors);
                    const company = getTextFromSelectors(companySelectors);
                    const location = getTextFromSelectors(locationSelectors);
                    const url = getHrefFromSelectors(urlSelectors);
                    const description = getTextFromSelectors(descriptionSelectors);
                    const postedAt = getTextFromSelectors(dateSelectors);
                    
                    // Only include jobs with essential data
                    if (title && company && url) {{
                        results.push({{
                            id: `linkedin_${{url.split('?')[0].split('/').pop()}}`,
                            title: title,
                            company: company,
                            location: location || 'Not specified',
                            url: url.split('?')[0], // Remove tracking parameters
                            description: description,
                            posted_at: postedAt,
                            source: 'linkedin',
                            scraped_at: new Date().toISOString()
                        }});
                    }}
                }} catch (e) {{
                    console.log(`Error processing job card ${{i}}: ${{e.message}}`);
                }}
            }}
            
            console.log(`Extracted ${{results.length}} valid jobs`);
            return results;
        }}, {limit});
        
        console.error(`✅ Extracted ${{jobs.length}} jobs`);
        
        // Output the results as JSON
        console.log(JSON.stringify(jobs));
        
    }} catch (error) {{
        console.error('❌ Error occurred:', error.message);
        console.log(JSON.stringify([])); // Return empty array on error
    }} finally {{
        if (browser) {{
            await browser.close();
            console.error('👋 Browser closed');
        }}
    }}
}}

// Run the scraper
scrapeLinkedIn();
"""

    def _build_linkedin_search_url(
        self, 
        keywords: str, 
        location: str, 
        experience_level: str, 
        job_type: str, 
        date_posted: str
    ) -> str:
        """Build LinkedIn job search URL with proper filters."""
        base_url = "https://www.linkedin.com/jobs/search"
        params = {
            "keywords": keywords,
            "location": location,
            "f_TPR": "r604800"  # Default to past week
        }

        # Map date posted to LinkedIn's format
        if date_posted:
            date_map = {
                "day": "r86400",      # Past 24 hours
                "week": "r604800",    # Past week  
                "month": "r2592000"   # Past month
            }
            params["f_TPR"] = date_map.get(date_posted.lower(), "r604800")

        # Map experience level
        if experience_level:
            exp_map = {
                "entry": "1",
                "associate": "2", 
                "mid": "3,4",
                "senior": "4,5",
                "director": "5,6",
                "executive": "6"
            }
            exp_value = exp_map.get(experience_level.lower())
            if exp_value:
                params["f_E"] = exp_value

        # Map job type
        if job_type:
            type_map = {
                "full-time": "F",
                "part-time": "P",
                "contract": "C", 
                "temporary": "T",
                "internship": "I"
            }
            type_value = type_map.get(job_type.lower())
            if type_value:
                params["f_JT"] = type_value
        
        # Remove None values before encoding
        params = {k: v for k, v in params.items() if v}
        
        search_url = f"{base_url}?{urlencode(params)}"
        logger.debug("Built LinkedIn search URL", url=search_url)
        return search_url

    def _validate_and_clean_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean extracted job data."""
        validated_jobs = []
        seen_urls = set()
        
        for job in jobs:
            try:
                job_url = job.get("url", "")
                if not job_url or job_url in seen_urls:
                    continue
                
                cleaned_job = {
                    "id": self._clean_text(job.get("id", "")),
                    "title": self._clean_text(job.get("title", "")),
                    "company": self._clean_text(job.get("company", "")),
                    "location": self._clean_text(job.get("location", "Not specified")),
                    "url": job_url.split('?')[0],  # Remove tracking params
                    "description": self._clean_text(job.get("description", "")),
                    "source": "linkedin",
                    "posted_at": self._parse_date(job.get("posted_at")),
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Only add if we have essential fields
                if cleaned_job["title"] and cleaned_job["company"]:
                    validated_jobs.append(cleaned_job)
                    seen_urls.add(job_url)
                    
            except Exception as e:
                logger.warning(f"Error processing job: {e}")
                continue
        
        logger.info(f"Validated {len(validated_jobs)} out of {len(jobs)} jobs")
        return validated_jobs

    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text content."""
        if not text:
            return None
        return re.sub(r'\s+', ' ', str(text).strip())

    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse relative dates like '2 days ago' into ISO format."""
        if not date_str:
            return None
        
        try:
            date_str = str(date_str).lower()
            now = datetime.now()
            
            if "hour" in date_str:
                hours = int(re.search(r'\d+', date_str).group())
                return (now - timedelta(hours=hours)).isoformat()
            elif "day" in date_str:
                days = int(re.search(r'\d+', date_str).group())
                return (now - timedelta(days=days)).isoformat()
            elif "week" in date_str:
                weeks = int(re.search(r'\d+', date_str).group())
                return (now - timedelta(weeks=weeks)).isoformat()
            elif "month" in date_str:
                months = int(re.search(r'\d+', date_str).group())
                return (now - timedelta(days=months * 30)).isoformat()
                
        except Exception as e:
            logger.warning(f"Could not parse date: {date_str}, error: {e}")
            
        return datetime.now().isoformat()

    async def _rate_limit(self):
        """Ensure a minimum delay between requests."""
        if self.last_request_time:
            elapsed = datetime.now().timestamp() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = datetime.now().timestamp()

    async def close(self):
        """Close any resources."""
        logger.info("LinkedIn scraper session closed")

# Global instance for use across the application
linkedin_scraper_v2 = LinkedInScraperV2()