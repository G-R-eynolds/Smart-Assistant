
const puppeteer = require('puppeteer-core');

async function scrapeLinkedIn() {
    console.error('🚀 Starting LinkedIn scraper...');
    
    let browser;
    try {
        // Connect to Bright Data's Scraping Browser
        console.error('🌐 Connecting to Bright Data Scraping Browser...');
        browser = await puppeteer.connect({
            browserWSEndpoint: 'wss://brd-customer-hl_39fbe0f0-zone-scraping_browser1:qbdnvm6s85i0@brd.superproxy.io:9222'
        });
        console.error('✅ Connected to browser');
        
        // Create a new page
        const page = await browser.newPage();
        
        // Set a realistic user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Navigate to LinkedIn job search
        console.error('🌐 Navigating to LinkedIn...');
        await page.goto('https://www.linkedin.com/jobs/search?keywords=software+engineer&location=San+Francisco&f_TPR=r604800', { 
            waitUntil: 'networkidle2', 
            timeout: 60000 
        });
        console.error('✅ Page loaded');
        
        // Wait for job cards to appear
        console.error('⏳ Waiting for job cards to load...');
        try {
            await page.waitForSelector('.job-search-card, .base-card, [data-testid="job-card"]', { 
                timeout: 30000 
            });
            console.error('✅ Job cards found');
        } catch (e) {
            console.error('⚠️ No job cards found, proceeding anyway...');
        }
        
        // Scroll to load more jobs
        console.error('📜 Scrolling to load more jobs...');
        for (let i = 0; i < 3; i++) {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await page.waitForTimeout(2000);
        }
        
        // Extract job data
        console.error('📊 Extracting job data...');
        const jobs = await page.evaluate((limit) => {
            const jobCards = document.querySelectorAll(
                '.job-search-card, .base-card, [data-testid="job-card"], .base-search-card'
            );
            const results = [];
            
            console.log(`Found ${jobCards.length} job cards`);
            
            for (let i = 0; i < Math.min(jobCards.length, limit); i++) {
                const card = jobCards[i];
                
                try {
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
                    const getTextFromSelectors = (selectors) => {
                        for (const selector of selectors) {
                            const element = card.querySelector(selector);
                            if (element) {
                                return element.textContent?.trim() || '';
                            }
                        }
                        return '';
                    };
                    
                    // Helper function to get href from multiple selectors
                    const getHrefFromSelectors = (selectors) => {
                        for (const selector of selectors) {
                            const element = card.querySelector(selector);
                            if (element && element.href) {
                                return element.href;
                            }
                        }
                        return '';
                    };
                    
                    const title = getTextFromSelectors(titleSelectors);
                    const company = getTextFromSelectors(companySelectors);
                    const location = getTextFromSelectors(locationSelectors);
                    const url = getHrefFromSelectors(urlSelectors);
                    const description = getTextFromSelectors(descriptionSelectors);
                    const postedAt = getTextFromSelectors(dateSelectors);
                    
                    // Only include jobs with essential data
                    if (title && company && url) {
                        results.push({
                            id: `linkedin_${url.split('?')[0].split('/').pop()}`,
                            title: title,
                            company: company,
                            location: location || 'Not specified',
                            url: url.split('?')[0], // Remove tracking parameters
                            description: description,
                            posted_at: postedAt,
                            source: 'linkedin',
                            scraped_at: new Date().toISOString()
                        });
                    }
                } catch (e) {
                    console.log(`Error processing job card ${i}: ${e.message}`);
                }
            }
            
            console.log(`Extracted ${results.length} valid jobs`);
            return results;
        }, 1);
        
        console.error(`✅ Extracted ${jobs.length} jobs`);
        
        // Output the results as JSON
        console.log(JSON.stringify(jobs));
        
    } catch (error) {
        console.error('❌ Error occurred:', error.message);
        console.log(JSON.stringify([])); // Return empty array on error
    } finally {
        if (browser) {
            await browser.close();
            console.error('👋 Browser closed');
        }
    }
}

// Run the scraper
scrapeLinkedIn();
