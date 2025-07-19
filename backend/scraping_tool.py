"""
Web scraping tool using Playwright with Bright Data proxy integration.
Provides async function to scrape page content through Bright Data's browser infrastructure.
"""

import asyncio
import os
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def load_env_variables():
    """Load environment variables from the project root .env file if not already loaded."""
    if not os.getenv('BRIGHTDATA_AUTH'):
        from dotenv import load_dotenv
        # Load from project root (one level up from this file)
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)


def load_brightdata_config():
    """Load Bright Data authentication and host details from environment variables."""
    # Ensure environment variables are loaded
    load_env_variables()
    
    brightdata_auth = os.getenv('BRIGHTDATA_AUTH')
    brightdata_host = os.getenv('BRIGHTDATA_HOST')
    
    if not brightdata_auth or not brightdata_host:
        raise ValueError(
            "BRIGHTDATA_AUTH and BRIGHTDATA_HOST environment variables must be set. "
            "Please check your .env file."
        )
    
    return brightdata_auth, brightdata_host


async def scrape_page_content(url: str) -> str:
    """
    Core browser interaction function to scrape page content.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        str: The full HTML content of the page
        
    Raises:
        ValueError: If Bright Data configuration is missing
        Exception: If scraping fails
    """
    # Load Bright Data auth and host details from environment variables
    brightdata_auth, brightdata_host = load_brightdata_config()
    
    # Construct the browser WebSocket endpoint URL
    browser_url = f'wss://{brightdata_auth}@{brightdata_host}'
    
    async with async_playwright() as p:
        # Connect to the Chromium browser using Bright Data's browser
        browser = await p.chromium.connect_over_cdp(browser_url)
        
        try:
            # Create a new page
            page = await browser.new_page()
            
            # Navigate to the provided URL with extended timeout
            await page.goto(url, timeout=120000)
            
            # Wait for the network to be idle to ensure all JavaScript has loaded
            await page.wait_for_load_state('networkidle')
            
            # Get the page's full HTML content
            content = await page.content()
            
            return content
            
        finally:
            # Ensure the browser is closed
            await browser.close()


async def scrape_and_parse(url: str) -> dict:
    """
    Enhanced scraping function that also parses the HTML content.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        dict: Parsed content including title, text, and raw HTML
    """
    try:
        # Get the raw HTML content
        html_content = await scrape_page_content(url)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract useful information
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get clean text content
        text_content = soup.get_text()
        # Clean up whitespace
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)
        
        return {
            'url': url,
            'title': title_text,
            'text_content': clean_text,
            'html_content': html_content,
            'content_length': len(clean_text),
            'success': True
        }
        
    except Exception as e:
        return {
            'url': url,
            'title': None,
            'text_content': None,
            'html_content': None,
            'content_length': 0,
            'success': False,
            'error': str(e)
        }


def scrape_sync(url: str) -> str:
    """
    Synchronous wrapper for the async scrape_page_content function.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        str: The HTML content of the page
    """
    return asyncio.run(scrape_page_content(url))


def scrape_and_parse_sync(url: str) -> dict:
    """
    Synchronous wrapper for the async scrape_and_parse function.
    
    Args:
        url (str): The URL to scrape
        
    Returns:
        dict: Parsed content including title, text, and raw HTML
    """
    return asyncio.run(scrape_and_parse(url))


def parse_job_search_results(html: str) -> list:
    """
    Parse LinkedIn job search results page HTML.
    
    Args:
        html (str): The HTML from a LinkedIn search results page
        
    Returns:
        list: List of dictionaries containing job title, company, location, and url
    """
    jobs = []
    
    try:
        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the main list container
        main_list = soup.find('ul', class_='jobs-search__results-list')
        
        if not main_list:
            print("⚠️  Could not find jobs search results list")
            return jobs
        
        # Iterate through all li elements within that list
        for li in main_list.find_all('li'):
            try:
                # Find the div with class base-search-card__info
                info_div = li.find('div', class_='base-search-card__info')
                
                if not info_div:
                    continue
                
                # Extract job title from h3 with class base-search-card__title
                title_h3 = info_div.find('h3', class_='base-search-card__title')
                job_title = title_h3.get_text().strip() if title_h3 else "No title"
                
                # Extract company from h4 with class base-search-card__subtitle
                company_h4 = info_div.find('h4', class_='base-search-card__subtitle')
                company = company_h4.get_text().strip() if company_h4 else "No company"
                
                # Extract location from span with class job-search-card__location
                location_span = info_div.find('span', class_='job-search-card__location')
                location = location_span.get_text().strip() if location_span else "No location"
                
                # Find the a tag that is a parent of the info card and get its href attribute
                job_url = "No URL"
                # Look for anchor tag that contains the info div or is a parent
                anchor = li.find('a', href=True)
                if anchor and anchor.get('href'):
                    job_url = anchor['href']
                    # Ensure it's a full URL
                    if job_url.startswith('/'):
                        job_url = f"https://www.linkedin.com{job_url}"
                
                # Create job dictionary
                job_data = {
                    'title': job_title,
                    'company': company,
                    'location': location,
                    'url': job_url
                }
                
                jobs.append(job_data)
                
            except Exception as e:
                print(f"⚠️  Error parsing job listing: {e}")
                continue
        
        print(f"✅ Successfully parsed {len(jobs)} job listings")
        
    except Exception as e:
        print(f"❌ Error parsing job search results: {e}")
    
    return jobs


def parse_job_description_page(html: str) -> str:
    """
    Parse LinkedIn job description page HTML.
    
    Args:
        html (str): The HTML from an individual job posting page
        
    Returns:
        str: The cleaned job description text
    """
    try:
        # Use BeautifulSoup to parse the HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the main description container
        description_div = soup.find('div', class_='show-more-less-html__markup')
        
        if not description_div:
            # Try alternative selectors for job description
            alternative_selectors = [
                'div[class*="description"]',
                'div[class*="job-description"]',
                'div[class*="job-details"]',
                'section[class*="description"]'
            ]
            
            for selector in alternative_selectors:
                description_div = soup.select_one(selector)
                if description_div:
                    break
        
        if not description_div:
            print("⚠️  Could not find job description container")
            return "No job description found"
        
        # Remove any script or style tags
        for script in description_div(["script", "style"]):
            script.decompose()
        
        # Extract all the text from this container
        description_text = description_div.get_text()
        
        # Clean up the text
        lines = (line.strip() for line in description_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = ' '.join(chunk for chunk in chunks if chunk)
        
        print(f"✅ Successfully extracted job description ({len(cleaned_text)} characters)")
        return cleaned_text
        
    except Exception as e:
        print(f"❌ Error parsing job description: {e}")
        return f"Error parsing job description: {str(e)}"


# Example usage and testing
async def test_scraping():
    """Test the scraping functionality with a sample URL."""
    test_url = "https://httpbin.org/html"
    
    print(f"🔍 Testing scraping functionality with: {test_url}")
    print("=" * 60)
    
    try:
        # Test basic scraping
        print("1. Testing basic HTML content retrieval...")
        html_content = await scrape_page_content(test_url)
        print(f"   ✅ Successfully retrieved {len(html_content)} characters")
        
        # Test enhanced parsing
        print("\\n2. Testing enhanced parsing...")
        parsed_result = await scrape_and_parse(test_url)
        
        if parsed_result['success']:
            print(f"   ✅ Successfully parsed content")
            print(f"   📄 Title: {parsed_result['title']}")
            print(f"   📝 Text length: {parsed_result['content_length']} characters")
            print(f"   🔗 URL: {parsed_result['url']}")
        else:
            print(f"   ❌ Parsing failed: {parsed_result['error']}")
            
    except Exception as e:
        print(f"❌ Scraping test failed: {e}")
        print("   Make sure BRIGHTDATA_AUTH and BRIGHTDATA_HOST are set in .env")


def test_job_parsing():
    """Test the LinkedIn job parsing functions with sample HTML."""
    print("\\n🧪 Testing LinkedIn Job Parsing Functions")
    print("=" * 60)
    
    # Sample LinkedIn job search results HTML structure
    sample_search_html = '''
    <ul class="jobs-search__results-list">
        <li>
            <a href="/jobs/view/1234567890">
                <div class="base-search-card__info">
                    <h3 class="base-search-card__title">Senior Software Engineer</h3>
                    <h4 class="base-search-card__subtitle">Tech Company Inc.</h4>
                    <span class="job-search-card__location">San Francisco, CA</span>
                </div>
            </a>
        </li>
        <li>
            <a href="/jobs/view/0987654321">
                <div class="base-search-card__info">
                    <h3 class="base-search-card__title">Python Developer</h3>
                    <h4 class="base-search-card__subtitle">Startup LLC</h4>
                    <span class="job-search-card__location">Remote</span>
                </div>
            </a>
        </li>
    </ul>
    '''
    
    # Sample LinkedIn job description HTML structure
    sample_description_html = '''
    <div class="show-more-less-html__markup">
        <p>We are looking for a talented Senior Software Engineer to join our team.</p>
        <ul>
            <li>5+ years of experience in Python</li>
            <li>Experience with Django/Flask</li>
            <li>Strong problem-solving skills</li>
        </ul>
        <p>Join us and make an impact!</p>
    </div>
    '''
    
    print("1. Testing job search results parsing...")
    jobs = parse_job_search_results(sample_search_html)
    
    if jobs:
        print(f"   ✅ Found {len(jobs)} jobs")
        for i, job in enumerate(jobs, 1):
            print(f"   Job {i}:")
            print(f"     Title: {job['title']}")
            print(f"     Company: {job['company']}")
            print(f"     Location: {job['location']}")
            print(f"     URL: {job['url']}")
    else:
        print("   ⚠️  No jobs found in sample HTML")
    
    print("\\n2. Testing job description parsing...")
    description = parse_job_description_page(sample_description_html)
    print(f"   Description: {description[:100]}...")
    
    return jobs, description


if __name__ == "__main__":
    print("🧪 Testing Web Scraping Tool")
    print("=" * 50)
    
    # Check environment variables
    try:
        brightdata_auth, brightdata_host = load_brightdata_config()
        print("✅ Bright Data configuration loaded")
        print(f"   Host: {brightdata_host}")
        print(f"   Auth: {brightdata_auth[:20]}...")
        
        # Test LinkedIn parsing functions first (no network required)
        test_job_parsing()
        
        # Run async test
        asyncio.run(test_scraping())
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\\n📋 Setup Instructions:")
        print("   1. Add BRIGHTDATA_AUTH to your .env file")
        print("   2. Add BRIGHTDATA_HOST to your .env file")
        print("   3. Ensure you have active Bright Data proxy access")
        
        # Still test parsing functions even if config is missing
        print("\\n🧪 Testing parsing functions (no network required):")
        test_job_parsing()
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
