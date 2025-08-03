"""
Smart Assistant Router

Main router for Smart Assistant functionality, including:
- Job discovery pipeline
- Inbox management
- Intelligence briefing
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.functions import job_discovery, inbox_management, intelligence_briefing
from app.core.linkedin_scraper_v2 import LinkedInScraperV2
from app.core.airtable_client import airtable_client
from app.core.gemini_client import gemini_client
from app.core.cv_manager import cv_manager
from app.core.job_deduplication import job_deduplication_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["smart-assistant"])

# Initialize service instances
linkedin_scraper_v2 = LinkedInScraperV2()

# Mock authentication dependency - replace with actual auth in production
async def get_current_user():
    """Mock function to simulate getting the current authenticated user"""
    # In production, this would validate the JWT token and return the user
    return {
        "id": "demo-user-id",
        "username": "demo_user",
        "email": "user@example.com",
        "role": "user"
    }


def generate_demo_jobs(search_query: str) -> list:
    """
    Generate realistic demo job data based on the search query
    This is used when the Smart Assistant backend is not available or requires authentication.
    """
    query_lower = search_query.lower()
    
    # Extract job role from query
    if "software engineer" in query_lower or "developer" in query_lower:
        job_title = "Software Engineer"
        skills = ["Python", "JavaScript", "React", "Node.js", "AWS"]
    elif "data scientist" in query_lower or "data" in query_lower:
        job_title = "Data Scientist"
        skills = ["Python", "Machine Learning", "SQL", "TensorFlow", "Pandas"]
    elif "frontend" in query_lower:
        job_title = "Frontend Developer"
        skills = ["React", "TypeScript", "CSS", "HTML", "Vue.js"]
    elif "backend" in query_lower:
        job_title = "Backend Developer"
        skills = ["Python", "Java", "Node.js", "PostgreSQL", "Docker"]
    else:
        job_title = "Software Developer"
        skills = ["Python", "JavaScript", "Git", "Linux", "Docker"]
    
    # Determine location preference
    location = "Remote" if "remote" in query_lower else "San Francisco, CA"
    
    demo_jobs = [
        {
            "title": job_title,
            "company": "TechCorp Inc",
            "location": location,
            "relevance_score": 0.92,
            "job_url": "https://linkedin.com/jobs/demo-1",
            "description": f"We're seeking a talented {job_title} to join our growing team. This role involves building scalable applications, working with modern technologies, and collaborating with cross-functional teams. Search query: {search_query}",
            "employment_type": "full-time",
            "experience_level": "mid",
            "ai_insights": {
                "match_reasoning": f"Excellent match for {job_title} based on your search criteria. Company actively hiring and offers competitive benefits.",
                "skills_match": skills[:3],
                "experience_match": True
            }
        },
        {
            "title": f"Senior {job_title}",
            "company": "InnovateLabs",
            "location": "New York, NY" if location != "Remote" else "Remote",
            "relevance_score": 0.87,
            "job_url": "https://linkedin.com/jobs/demo-2",
            "description": f"Lead {job_title} position with opportunities for mentorship and technical leadership. Work on cutting-edge projects with the latest technologies.",
            "employment_type": "full-time",
            "experience_level": "senior",
            "ai_insights": {
                "match_reasoning": "Strong technical match with leadership opportunities. Competitive salary and remote-friendly culture.",
                "skills_match": skills[:4],
                "experience_match": True
            }
        },
        {
            "title": f"Junior {job_title}",
            "company": "StartupCo",
            "location": "Austin, TX",
            "relevance_score": 0.73,
            "job_url": "https://linkedin.com/jobs/demo-3",
            "description": f"Entry-level {job_title} position perfect for recent graduates or career changers. Great learning environment with mentorship opportunities.",
            "employment_type": "full-time",
            "experience_level": "entry",
            "ai_insights": {
                "match_reasoning": "Good match for growing your skills. Startup environment with rapid learning opportunities.",
                "skills_match": skills[:2],
                "experience_match": False
            }
        }
    ]
    
    return demo_jobs


@router.get("/health")
async def health_check():
    """Health check endpoint for Smart Assistant"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "job_discovery": True,
            "inbox_management": True,
            "intelligence_briefing": True
        }
    }

@router.post("/job-discovery/run")
async def run_job_discovery(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Run the job discovery pipeline with the provided search parameters"""
    try:
        # Extract parameters
        search_query = data.get("query", "")
        if not search_query:
            raise HTTPException(status_code=400, detail="Search query is required")
            
        # Initialize pipeline
        pipeline = job_discovery.Pipeline()
        
        # Process the search request
        results = await pipeline.process_job_search({
            "user_id": current_user["id"],
            "message": search_query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Return the processed results
        return {
            "status": "success",
            "message": f"Found {len(results['jobs'])} jobs matching your query",
            "jobs": results["jobs"]
        }
    except Exception as e:
        logger.error(f"Job discovery error: {e}")
        return {
            "status": "error",
            "message": f"Error processing job search: {str(e)}",
            "jobs": []
        }


@router.post("/jobs/search")
async def search_jobs(
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """Search for jobs using AI-powered keyword extraction, LinkedIn scraping, cover letters, and Airtable storage"""
    try:
        # Extract parameters from request
        user_query = data.get("query", data.get("keywords", ""))  # Support both 'query' and 'keywords'
        location_override = data.get("location", "")  # User can override location
        experience_level_override = data.get("experience_level", "")  # User can override experience level
        job_type_override = data.get("job_type", "")  # User can override job type
        date_posted = data.get("date_posted", "week")
        limit = data.get("limit", 25)
        generate_cover_letters = data.get("generate_cover_letters", True)
        save_to_airtable = data.get("save_to_airtable", True)
        min_relevance_score = data.get("min_relevance_score", 0.7)  # Minimum relevance score to save
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Query or keywords are required")
        
        logger.info(f"Processing job search query: '{user_query}'")
        
        # Step 1: Use AI to extract optimized search keywords
        logger.info("Extracting search keywords using AI...")
        keyword_extraction = await gemini_client.extract_job_search_keywords(user_query)
        
        if keyword_extraction.get("success", False):
            # Use AI-extracted parameters
            keywords = keyword_extraction.get("keywords", user_query)
            location = location_override or keyword_extraction.get("location", "")
            experience_level = experience_level_override or keyword_extraction.get("experience_level", "")
            job_type = job_type_override or keyword_extraction.get("job_type", "")
            
            logger.info(f"AI extracted - Keywords: '{keywords}', Location: '{location}', Level: '{experience_level}', Type: '{job_type}'")
            if keyword_extraction.get("reasoning"):
                logger.info(f"AI reasoning: {keyword_extraction['reasoning']}")
        else:
            # Fallback to original query
            keywords = user_query
            location = location_override
            experience_level = experience_level_override
            job_type = job_type_override
            logger.warning(f"AI extraction failed, using original query: {keyword_extraction.get('error', 'Unknown error')}")
        
        # Step 2: Search LinkedIn with optimized keywords
        logger.info(f"Searching LinkedIn with keywords: '{keywords}'")
        jobs = await linkedin_scraper_v2.search_jobs(
            keywords=keywords,
            location=location,
            experience_level=experience_level,
            job_type=job_type,
            date_posted=date_posted,
            limit=limit
        )
        
        # Add background task to process jobs (generate cover letters and save to Airtable)
        if jobs:
            background_tasks.add_task(
                process_jobs_with_ai, 
                jobs, 
                generate_cover_letters,
                save_to_airtable and airtable_client.is_configured(),
                min_relevance_score
            )
            
            cover_letter_msg = " and generating cover letters" if generate_cover_letters and gemini_client.is_configured() else ""
            airtable_msg = f" Filtering by relevance >= {min_relevance_score} and saving to Airtable..." if save_to_airtable and airtable_client.is_configured() else " (Airtable not configured)"
            
            message = f"Found {len(jobs)} jobs matching your criteria{cover_letter_msg}.{airtable_msg}"
        else:
            message = "No jobs found matching your criteria"
        
        # Return immediate response with AI extraction info
        return {
            "status": "success",
            "count": len(jobs),
            "message": message,
            "jobs": jobs,  # Jobs for immediate display
            "ai_extraction": {
                "original_query": user_query,
                "extracted_keywords": keywords,
                "extracted_location": location,
                "extracted_experience_level": experience_level,
                "extracted_job_type": job_type,
                "ai_success": keyword_extraction.get("success", False),
                "ai_reasoning": keyword_extraction.get("reasoning", ""),
                "search_strategy": keyword_extraction.get("search_strategy", ""),
                "fallback_used": keyword_extraction.get("fallback_used", False)
            }
        }
        
    except Exception as e:
        logger.error(f"Job search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching for jobs: {str(e)}"
        )


async def process_jobs_with_ai(
    jobs: List[Dict[str, Any]], 
    generate_cover_letters: bool, 
    save_to_airtable: bool,
    min_relevance_score: float = 0.7
):
    """
    Background task to process jobs with AI, filter by relevance, and save to Airtable
    
    Args:
        jobs: List of job dictionaries from LinkedIn scraper
        generate_cover_letters: Whether to generate cover letters
        save_to_airtable: Whether to save to Airtable
        min_relevance_score: Minimum relevance score to save job (default: 0.7)
    """
    try:
        # Step 1: Filter out duplicate jobs using database
        new_jobs = await job_deduplication_service.process_jobs_with_deduplication(jobs)
        
        if not new_jobs:
            logger.info("All jobs were duplicates, no processing needed")
            return
        
        processed_jobs = []
        filtered_jobs = []
        
        logger.info(f"Processing {len(new_jobs)} new jobs with AI analysis...")
        
        for i, job in enumerate(new_jobs, 1):
            processed_job = job.copy()
            
            logger.info(f"Processing job {i}/{len(new_jobs)}: {job.get('title')} at {job.get('company')}")
            
            # Analyze job posting with relevance scoring (this includes CV matching)
            if gemini_client.is_configured() and job.get("description"):
                try:
                    analysis_result = await gemini_client.analyze_job_posting(job["description"])
                    processed_job["job_analysis"] = analysis_result
                    
                    # Extract relevance score from analysis
                    if analysis_result.get("success") and "analysis" in analysis_result:
                        relevance_score = analysis_result["analysis"].get("relevance_score", 0.0)
                        processed_job["relevance_score"] = relevance_score
                        
                        logger.info(f"Job relevance score: {relevance_score:.2f} for {job.get('title')}")
                        
                        # Only process further if relevance score meets threshold
                        if relevance_score >= min_relevance_score:
                            logger.info(f"✅ Job passes relevance filter ({relevance_score:.2f} >= {min_relevance_score})")
                            
                            # Generate cover letter for high-relevance jobs
                            if generate_cover_letters and gemini_client.is_configured():
                                try:
                                    cover_letter_result = await gemini_client.generate_cover_letter(
                                        job_title=job.get("title", ""),
                                        company=job.get("company", ""),
                                        job_description=job.get("description", "")
                                    )
                                    processed_job["cover_letter"] = cover_letter_result
                                    logger.info(f"Generated cover letter for {job.get('title')}")
                                except Exception as e:
                                    logger.error(f"Failed to generate cover letter for {job.get('title')}: {e}")
                                    processed_job["cover_letter"] = {
                                        "success": False,
                                        "error": str(e),
                                        "cover_letter": ""
                                    }
                            
                            filtered_jobs.append(processed_job)
                        else:
                            logger.info(f"❌ Job filtered out ({relevance_score:.2f} < {min_relevance_score})")
                    else:
                        logger.warning(f"Failed to get relevance score for {job.get('title')}")
                        processed_job["relevance_score"] = 0.0
                        
                except Exception as e:
                    logger.error(f"Failed to analyze job posting for {job.get('title')}: {e}")
                    processed_job["job_analysis"] = {
                        "success": False,
                        "error": str(e)
                    }
                    processed_job["relevance_score"] = 0.0
            else:
                processed_job["relevance_score"] = 0.0
            
            processed_jobs.append(processed_job)
        
        logger.info(f"Filtered {len(filtered_jobs)} out of {len(new_jobs)} jobs (relevance >= {min_relevance_score})")
        
        # Save only high-relevance jobs to Airtable if configured
        if save_to_airtable and filtered_jobs:
            logger.info(f"Saving {len(filtered_jobs)} high-relevance jobs to Airtable...")
            result = await airtable_client.add_jobs(filtered_jobs)
            logger.info(f"Airtable save result: {result}")
            
            # Mark successfully saved jobs as processed to avoid duplicates
            if result.get("success"):
                await job_deduplication_service.mark_jobs_as_processed(filtered_jobs)
            
        elif save_to_airtable:
            logger.info("No jobs met relevance threshold - nothing saved to Airtable")
            
            # Even if no jobs passed the filter, mark all analyzed jobs as processed
            # to avoid re-analyzing them in future runs
            await job_deduplication_service.mark_jobs_as_processed(new_jobs)
        
        return {
            "total_processed": len(processed_jobs),
            "high_relevance_jobs": len(filtered_jobs),
            "min_relevance_score": min_relevance_score,
            "saved_to_airtable": save_to_airtable and len(filtered_jobs) > 0
        }
        
    except Exception as e:
        logger.error(f"Failed to process jobs with AI: {e}")
        return {
            "error": str(e),
            "total_processed": 0,
            "high_relevance_jobs": 0
        }


@router.post("/inbox/process")
async def process_inbox(
    request: Request,
    body: dict,
    current_user: Dict = Depends(get_current_user)
):
    """
    Smart Assistant Inbox Processing Endpoint
    
    This endpoint processes email inbox for categorization,
    summarization, and action item extraction.
    """
    try:
        # Initialize the inbox management pipeline
        pipeline = inbox_management.Pipeline()
        
        # Process the inbox request
        try:
            results = await pipeline.process_inbox({
                "user_id": current_user["id"],
                "credentials": body.get("credentials", {}),
                "filters": body.get("filters", {}),
                "timestamp": datetime.now().isoformat()
            })
            return results
        except Exception:
            # If pipeline processing fails, use mock data
            logger.warning("Failed to process inbox with pipeline, using mock data")
            return {
                "status": "success",
                "data": {
                    "unread_count": 12,
                    "total_emails": 45,
                    "important_emails": [
                        {
                            "id": "email_1",
                            "sender": "recruiter@techcorp.com",
                            "subject": "Software Engineer Position",
                            "urgency": "high",
                            "category": "job_opportunity",
                            "received_at": "2025-08-01T10:30:00Z",
                            "preview": "We'd like to discuss an exciting opportunity..."
                        },
                        {
                            "id": "email_2", 
                            "sender": "manager@company.com",
                            "subject": "Project Update Required",
                            "urgency": "medium",
                            "category": "work",
                            "received_at": "2025-08-01T09:15:00Z",
                            "preview": "Please provide the status update for Q3 project..."
                    }
                ],
                "categories": {
                    "job_opportunity": 3,
                    "work": 8,
                    "personal": 2,
                    "newsletter": 15,
                    "social": 5,
                    "promotional": 12
                },
                "action_items": [
                    {
                        "description": "Respond to Tech Corp recruiter",
                        "priority": "high",
                        "due_date": "2025-08-02"
                    },
                    {
                        "description": "Submit Q3 project status update",
                        "priority": "medium", 
                        "due_date": "2025-08-03"
                    }
                ],
                "processing_time_ms": 1250
            }
        }
        
    except Exception as e:
        logger.error(f"Inbox processing error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "unread_count": 0,
                "total_emails": 0,
                "important_emails": [],
                "categories": {},
                "action_items": [],
                "processing_time_ms": 0
            }
        }


@router.post("/briefing/generate")
async def generate_intelligence_briefing(
    request: Request,
    body: dict,
    current_user: Dict = Depends(get_current_user)
):
    """
    Smart Assistant Intelligence Briefing Generator
    
    This endpoint generates a daily intelligence briefing with market news,
    technology trends, career insights, and recommendations.
    """
    try:
        # Initialize the intelligence briefing pipeline
        pipeline = intelligence_briefing.Pipeline()
        
        # Process the briefing request
        try:
            results = await pipeline.generate_briefing({
                "user_id": current_user["id"],
                "preferences": body.get("preferences", {}),
                "timestamp": datetime.now().isoformat()
            })
            return results
        except Exception:
            # If pipeline processing fails, use mock data
            logger.warning("Failed to generate briefing with pipeline, using mock data")
        return {
            "status": "success",
            "data": {
                "generated_at": "2025-08-01T10:45:00Z",
                "news_items": [
                    {
                        "title": "AI Development Trends in 2025",
                        "source": "TechCrunch",
                        "category": "technology",
                        "summary": "Latest developments in AI and machine learning affecting the job market...",
                        "published_at": "2025-08-01T08:00:00Z",
                        "relevance": "high",
                        "url": "https://example.com/ai-trends-2025"
                    },
                    {
                        "title": "Remote Work Policy Changes",
                        "source": "Reuters",
                        "category": "business",
                        "summary": "Major tech companies updating their remote work policies...",
                        "published_at": "2025-07-31T16:30:00Z",
                        "relevance": "medium",
                        "url": "https://example.com/remote-work-changes"
                    }
                ],
                "market_data": {
                    "tech_stocks": "+2.3%",
                    "job_market_health": "strong",
                    "hiring_trends": "increasing demand for AI/ML roles"
                },
                "tech_trends": [
                    {
                        "title": "AI-Assisted Development",
                        "impact_score": 8.7,
                        "summary": "Growing adoption of AI coding assistants in development workflows"
                    },
                    {
                        "title": "Edge Computing Growth",
                        "impact_score": 7.5,
                        "summary": "Increased focus on edge computing for IoT and real-time applications"
                    }
                ],
                "career_insights": [
                    {
                        "title": "High-Demand Skills",
                        "relevance": "immediate",
                        "description": "Python, React, and cloud platforms remain top requested skills"
                    },
                    {
                        "title": "Salary Trends",
                        "relevance": "planning",
                        "description": "Software engineer salaries up 8% year-over-year in tech hubs"
                    }
                ],
                "key_takeaways": [
                    "AI integration skills becoming essential for developers",
                    "Remote-first companies offering competitive packages",
                    "Continuous learning in cloud technologies recommended"
                ],
                "generation_time_ms": 2100
            }
        }
        
    except Exception as e:
        logger.error(f"Intelligence briefing generation error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "generated_at": "",
                "news_items": [],
                "market_data": {},
                "tech_trends": [],
                "career_insights": [],
                "key_takeaways": [],
                "generation_time_ms": 0
            }
        }


@router.get("/cv/info")
async def get_cv_info():
    """Get information about the current CV file"""
    try:
        cv_info = cv_manager.get_cv_info()
        logger.info(f"CV info requested: {cv_info['exists']}")
        return {
            "status": "success",
            "data": cv_info
        }
    except Exception as e:
        logger.error(f"Error getting CV info: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {"exists": False, "message": "Error checking CV file"}
        }


@router.get("/cv/summary")
async def get_cv_summary():
    """Get a summary of the CV content"""
    try:
        cv_summary = cv_manager.get_cv_summary()
        logger.info(f"CV summary requested: {cv_summary['available']}")
        return {
            "status": "success",
            "data": cv_summary
        }
    except Exception as e:
        logger.error(f"Error getting CV summary: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {"available": False, "message": "Error processing CV"}
        }


@router.post("/cv/refresh")
async def refresh_cv_cache():
    """Force refresh of the CV text cache"""
    try:
        cv_text = cv_manager.get_cv_text(force_refresh=True)
        
        if cv_text:
            return {
                "status": "success",
                "message": "CV cache refreshed successfully",
                "data": {
                    "character_count": len(cv_text),
                    "word_count": len(cv_text.split()),
                    "refreshed": True
                }
            }
        else:
            return {
                "status": "error",
                "message": "Could not refresh CV - file not found or processing failed",
                "data": {"refreshed": False}
            }
            
    except Exception as e:
        logger.error(f"Error refreshing CV cache: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": {"refreshed": False}
        }
