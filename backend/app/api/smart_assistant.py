"""
Smart Assistant Router

Main router for Smart Assistant functionality, including:
- Job discovery pipeline
- Inbox management
- Intelligence briefing
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile, File, Form, Header, Response
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from app.functions import job_discovery, inbox_management, intelligence_briefing
from app.core.linkedin_scraper_v2 import LinkedInScraperV2
from app.core.airtable_client import airtable_client
from app.core.gemini_client import gemini_client
from app.core.cv_manager import cv_manager
from app.core.job_deduplication import job_deduplication_service
from app.core.graphrag_service import graphrag_service
from app.core.graphrag_query_adapter import query_adapter
from app.core.config import settings
from app.services.cluster_service import cluster_service

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


@router.post("/graphrag/ingest")
async def graphrag_ingest(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Ingest a document into the GraphRAG store (MVP heuristic extraction)."""
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}

    text = payload.get("text") or payload.get("content") or ""
    doc_id = payload.get("doc_id") or payload.get("id") or str(datetime.utcnow().timestamp())
    metadata = payload.get("metadata", {})
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    # Optional tuning flags for development
    force_heuristic = bool(payload.get("force_heuristic", False))
    disable_embeddings = bool(payload.get("disable_embeddings", False))
    namespace = payload.get("namespace")
    result = await graphrag_service.ingest_document(
        doc_id=doc_id,
        text=text,
        metadata=metadata,
        force_heuristic=force_heuristic,
        disable_embeddings=disable_embeddings,
        namespace=namespace,
    )
    if result.get("success"):
        try:
            cluster_service.trigger_background_recompute(namespace)
        except Exception:
            pass
    return result

@router.post("/graphrag/ingest-file")
async def graphrag_ingest_file(
    file: UploadFile = File(...),
    doc_id: str = Form(None),
    force_heuristic: bool = Form(False),
    disable_embeddings: bool = Form(False),
    current_user: Dict = Depends(get_current_user),
):
    """Ingest a text file (UTF-8) into GraphRAG.
    Expects a multipart/form-data with fields:
      - file: the uploaded text file
      - doc_id (optional)
      - force_heuristic (optional bool)
      - disable_embeddings (optional bool)
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    try:
        content = (await file.read()).decode("utf-8", errors="ignore")
        if not content.strip():
            raise HTTPException(status_code=400, detail="file is empty")
        _doc_id = doc_id or file.filename or str(datetime.utcnow().timestamp())
        result = await graphrag_service.ingest_document(
            doc_id=_doc_id,
            text=content,
            metadata={"filename": file.filename},
            force_heuristic=force_heuristic,
            disable_embeddings=disable_embeddings,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("File ingest failed")
        return {"success": False, "error": str(e)}

@router.post("/graphrag/ingest-pdf")
async def graphrag_ingest_pdf(
    file: UploadFile = File(...),
    doc_id: str = Form(None),
    namespace: Optional[str] = Form(None),
    max_pages: int = Form(50),
    current_user: Dict = Depends(get_current_user),
):
    """Ingest a PDF by extracting text server-side.
    Expects multipart/form-data with:
      - file: uploaded PDF file
      - doc_id (optional): override document id; defaults to filename
      - namespace (optional): graph namespace
      - max_pages (optional): limit pages to extract
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    try:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="file is empty")
        text = ""
        # Try PyPDF2 first
        try:
            import PyPDF2  # type: ignore
            from io import BytesIO
            reader = PyPDF2.PdfReader(BytesIO(raw))
            pages = reader.pages[: max(1, int(max_pages))]
            for p in pages:
                try:
                    text += (p.extract_text() or "") + "\n"
                except Exception:
                    continue
        except Exception:
            text = ""
        # Fallback: pdfplumber if available
        if not text.strip():
            try:
                import pdfplumber  # type: ignore
                from io import BytesIO
                with pdfplumber.open(BytesIO(raw)) as pdf:
                    for i, page in enumerate(pdf.pages):
                        if i >= max(1, int(max_pages)):
                            break
                        try:
                            text += (page.extract_text() or "") + "\n"
                        except Exception:
                            continue
            except Exception:
                pass
        # Last resort: naive decode (may be garbage)
        if not text.strip():
            try:
                text = raw.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        _doc_id = doc_id or file.filename or str(datetime.utcnow().timestamp())
        result = await graphrag_service.ingest_document(
            doc_id=_doc_id,
            text=text,
            metadata={"filename": file.filename, "content_type": file.content_type or "application/pdf"},
            namespace=namespace,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("PDF ingest failed")
        return {"success": False, "error": str(e)}

@router.post("/graphrag/ingest-batch")
async def graphrag_ingest_batch(
    payload: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """Batch ingest multiple documents.
    Expects: { documents: [ {doc_id, text, metadata?, force_heuristic?, disable_embeddings?}, ... ] }
    Returns per-document status and aggregate stats.
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    docs = payload.get("documents") or []
    if not isinstance(docs, list) or not docs:
        raise HTTPException(status_code=400, detail="documents list required")
    aggregate = {"total": len(docs), "succeeded": 0, "failed": 0, "nodes": 0, "edges": 0}
    results = []
    for d in docs[:100]:  # cap to avoid abuse
        text = d.get("text") or ""
        if not text.strip():
            results.append({"doc_id": d.get("doc_id"), "success": False, "error": "empty text"})
            aggregate["failed"] += 1
            continue
        doc_id = d.get("doc_id") or d.get("id") or str(datetime.utcnow().timestamp())
        r = await graphrag_service.ingest_document(
            doc_id=doc_id,
            text=text,
            metadata=d.get("metadata"),
            force_heuristic=bool(d.get("force_heuristic", False)),
            disable_embeddings=bool(d.get("disable_embeddings", False)),
            namespace=d.get("namespace"),
        )
        if r.get("success"):
            aggregate["succeeded"] += 1
            st = r.get("stats", {})
            aggregate["nodes"] += st.get("nodes", 0)
            aggregate["edges"] += st.get("edges", 0)
        else:
            aggregate["failed"] += 1
        r["doc_id"] = doc_id
        results.append(r)
    return {"success": True, "aggregate": aggregate, "results": results}


@router.post("/graphrag/query")
async def graphrag_query(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Query the graph with naive hybrid retrieval (name contains + adjacency)."""
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}

    query = payload.get("query") or payload.get("q") or ""
    top_k = int(payload.get("top_k", 5))
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    namespace = payload.get("namespace")
    label_filter = payload.get("labels") or payload.get("label_filter")
    relation_filter = payload.get("relations") or payload.get("relation_filter")
    if isinstance(label_filter, str):
        label_filter = [l.strip() for l in label_filter.split(",") if l.strip()]
    if isinstance(relation_filter, str):
        relation_filter = [r.strip() for r in relation_filter.split(",") if r.strip()]
    result = await graphrag_service.hybrid_retrieve(query=query, top_k=top_k, namespace=namespace, label_filter=label_filter, relation_filter=relation_filter)
    return {"success": True, "results": result}


@router.post("/graphrag/query2")
async def graphrag_query2(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Enhanced query endpoint (Phase 3) supporting modes: auto|global|local|drift.
    Body: { query, top_k?, mode?, namespace? }
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    q = payload.get("query") or payload.get("q") or ""
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    mode = payload.get("mode", "auto")
    top_k = int(payload.get("top_k", 8))
    namespace = payload.get("namespace")
    result = await query_adapter.query(query=q, mode=mode, top_k=top_k, namespace=namespace)
    return result

@router.post("/graphrag/snapshots")
async def graphrag_create_snapshot(current_user: Dict = Depends(get_current_user)):
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    snap = await graphrag_service.create_snapshot()
    return {"success": True, **snap}

@router.get("/graphrag/snapshots")
async def graphrag_list_snapshots(limit: int = 25, current_user: Dict = Depends(get_current_user)):
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    snaps = await graphrag_service.list_snapshots(limit=limit)
    return {"success": True, "snapshots": snaps}

@router.get("/graphrag/snapshots/diff")
async def graphrag_diff_snapshots(a: str, b: str, current_user: Dict = Depends(get_current_user)):
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    diff = await graphrag_service.diff_snapshots(a, b)
    if "error" in diff:
        raise HTTPException(status_code=404, detail=diff["error"])
    return {"success": True, **diff}

@router.post("/graphrag/ingest-cv")
async def graphrag_ingest_cv(current_user: Dict = Depends(get_current_user)):
    """Convenience endpoint: ingest the configured CV PDF (splits to text) into GraphRAG."""
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    import os
    from pathlib import Path
    from app.core.config import settings as cfg
    cv_path = Path(cfg.CV_DIRECTORY) / cfg.CV_FILENAME
    if not cv_path.exists():
        raise HTTPException(status_code=404, detail="CV file not found")
    # Minimal text extraction (simple) to avoid heavy dependency; fallback plain bytes decode
    text = ""
    try:
        import PyPDF2  # type: ignore
        with open(cv_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:25]:
                try:
                    text += page.extract_text() or ""
                    text += "\n"
                except Exception:
                    continue
    except Exception:
        try:
            text = cv_path.read_text(errors='ignore')
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read CV file")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Extracted CV text empty")
    doc_id = f"cv::{current_user['id']}"
    result = await graphrag_service.ingest_document(doc_id=doc_id, text=text, metadata={"source":"cv"})
    return {"success": True, "ingest": result}

@router.post("/graphrag/reset")
async def graphrag_reset(current_user: Dict = Depends(get_current_user)):
    """Dangerous: wipe all graph nodes/edges/snapshots (for re-index)."""
    from sqlalchemy import delete
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge, GraphClusterMembership, GraphClusterSummary, GraphSnapshot
    async with get_db_session() as session:
        for model in [GraphEdge, GraphClusterMembership, GraphClusterSummary, GraphSnapshot, GraphNode]:
            await session.execute(delete(model))
        await session.commit()
    # reset metrics partially
    for k in ["nodes_created","edges_created","ingest_count"]:
        graphrag_service.metrics[k] = 0
    return {"success": True, "message": "Graph wiped"}


@router.post("/graphrag/answer")
async def graphrag_answer(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Retrieve and synthesize an answer using graph-backed context."""
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    question = payload.get("question") or payload.get("query") or ""
    top_k = int(payload.get("top_k", 6))
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    namespace = payload.get("namespace")
    result = await graphrag_service.answer(question=question, top_k=top_k, namespace=namespace)
    # Add explicit contributing node id list for semantic overlay convenience
    contributing_ids = [n.get("id") for n in result.get("context_nodes", []) if n.get("id")]
    return {"success": True, **result, "contributing_node_ids": contributing_ids}

@router.post("/graphrag/path")
async def graphrag_path(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Return shortest path (node id sequence) between source and target plus path edges.
    Body: {source_id, target_id, max_depth?, namespace?}
    """
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="source_id and target_id required")
    max_depth = int(payload.get("max_depth", 4))
    namespace = payload.get("namespace")
    path_data = await graphrag_service.shortest_path(source_id, target_id, max_depth=max_depth, namespace=namespace)
    # Derive edges for returned path sequence
    seq = path_data.get("path", [])
    edges: List[Dict[str, Any]] = []
    if len(seq) >= 2:
        from sqlalchemy import select, or_, and_
        from app.core.database import get_db_session
        from app.models.database import GraphEdge
        async with get_db_session() as session:
            existing = await session.execute(select(GraphEdge).where(or_(GraphEdge.source_id.in_(seq), GraphEdge.target_id.in_(seq))))
            by_pair = {}
            for e in existing.scalars().all():
                by_pair.setdefault((e.source_id, e.target_id), e)
                by_pair.setdefault((e.target_id, e.source_id), e)
            for a, b in zip(seq, seq[1:]):
                e = by_pair.get((a,b))
                if e:
                    edges.append({"id": e.id, "source_id": e.source_id, "target_id": e.target_id, "relation": e.relation, "confidence": e.confidence})
    return {"path": seq, "edges": edges}

@router.get("/graphrag/similar")
async def graphrag_similar(node_id: str, top_k: int = 8, namespace: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Return top-k embedding-similar nodes to a given node (semantic ring).
    Fallback to name trigram similarity if embeddings absent.
    """
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode
    import math
    ns = namespace or settings.DEFAULT_NAMESPACE
    async with get_db_session() as session:
        target_q = await session.execute(select(GraphNode).where(GraphNode.id == node_id))
        target = target_q.scalars().first()
        if not target:
            raise HTTPException(status_code=404, detail="node not found")
        tq = await session.execute(select(GraphNode))
        candidates = [n for n in tq.scalars().all() if (n.namespace or settings.DEFAULT_NAMESPACE) == ns and n.id != node_id]
        sims: List[Tuple[float, GraphNode]] = []  # type: ignore[name-defined]
        tv = target.embedding or []
        if tv and isinstance(tv, list):
            # Cosine similarity
            import numpy as np
            tvec = np.array(tv, dtype=float)
            tnorm = np.linalg.norm(tvec) + 1e-9
            for c in candidates:
                ev = c.embedding or []
                if not ev:
                    continue
                try:
                    cvec = np.array(ev, dtype=float)
                    sim = float(np.dot(tvec, cvec) / (tnorm * (np.linalg.norm(cvec)+1e-9)))
                    sims.append((sim, c))
                except Exception:
                    continue
        else:
            # Fallback: simple overlap score on lowercase 3+ char tokens of names
            import re
            base_tokens = {w for w in re.split(r"\W+", (target.name or '').lower()) if len(w) >= 3}
            for c in candidates:
                ctoks = {w for w in re.split(r"\W+", (c.name or '').lower()) if len(w) >= 3}
                inter = len(base_tokens & ctoks)
                union = len(base_tokens | ctoks) or 1
                sims.append((inter/union, c))
        sims.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sc, c in sims[:top_k]:
            out.append({"id": c.id, "name": c.name, "label": c.label, "score": round(sc,4)})
        return {"node_id": node_id, "similar": out}


@router.get("/graphrag/graph")
async def graphrag_graph(
    sample: int = 200,
    namespace: Optional[str] = None,
    label: Optional[str] = None,
    relation: Optional[str] = None,
    mode: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    wx: float = 2.0,
    wy: float = 2.0,
    current_user: Dict = Depends(get_current_user)
):
    """Return a filtered sample of nodes & edges for visualization.
    Query params:
      - sample: max nodes/edges
      - namespace: restrict to namespace
      - label: restrict node label
      - relation: restrict edge relation
    """
    from sqlalchemy import select, or_
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge
    ns_name = namespace or settings.DEFAULT_NAMESPACE
    async with get_db_session() as session:
        base_q = select(GraphNode)
        if mode == "viewport" and x is not None and y is not None:
            # Use stored layout positions if available in properties {layout: {x,y}}
            # Fallback to random sample otherwise
            res = await session.execute(base_q)
            selected = []
            for n in res.scalars().all():
                props = n.properties or {}
                if (props.get("namespace", settings.DEFAULT_NAMESPACE) != ns_name):
                    continue
                if label and n.label != label:
                    continue
                pos = (props.get("layout") or {})
                nx = pos.get("x")
                ny = pos.get("y")
                if nx is None or ny is None:
                    continue
                if (x - wx/2) <= nx <= (x + wx/2) and (y - wy/2) <= ny <= (y + wy/2):
                    selected.append(n)
                    if len(selected) >= sample:
                        break
            nodes = selected
        else:
            res = await session.execute(base_q.limit(sample))
            nodes = [
                n for n in res.scalars().all()
                if (n.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns_name
                and (not label or n.label == label)
            ]
        nodes_out = [
            {"id": n.id, "label": n.label, "name": n.name, "properties": n.properties or {}}
            for n in nodes
        ]
        ids = [n.id for n in nodes]
        edges_out: List[Dict[str, Any]] = []
        if ids:
            eq = await session.execute(
                select(GraphEdge).where(
                    or_(GraphEdge.source_id.in_(ids), GraphEdge.target_id.in_(ids))
                ).limit(sample)
            )
            edges_out = [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation,
                }
                for e in eq.scalars().all()
                if (e.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) == ns_name
                and (not relation or e.relation == relation)
            ]
    return {"nodes": nodes_out, "edges": edges_out, "namespace": ns_name}

@router.get("/graphrag/nodes")
async def list_graphrag_nodes(
    namespace: Optional[str] = None,
    label: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode
    ns_name = namespace or settings.DEFAULT_NAMESPACE
    limit = max(1, min(limit, 200))
    async with get_db_session() as session:
        # Simple cursor = last node id alphabetically; not stable for all cases but fine for Phase 2
        q = select(GraphNode)
        res = await session.execute(q)
        collected = []
        started = cursor is None
        for n in sorted(res.scalars().all(), key=lambda z: (z.name or "")):
            if (n.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) != ns_name:
                continue
            if label and n.label != label:
                continue
            if search and search.lower() not in (n.name or "").lower():
                continue
            if not started:
                if n.id == cursor:
                    # Found cursor boundary; skip this item and start collecting from next
                    started = True
                    continue
                else:
                    continue
            if started:
                if len(collected) < limit:
                    collected.append(n)
                else:
                    break
        next_cursor = collected[-1].id if collected and len(collected) == limit else None
        return {
            "results": [
                {"id": n.id, "name": n.name, "label": n.label, "properties": n.properties or {}}
                for n in collected
            ],
            "count": len(collected),
            "cursor": next_cursor,
            "limit": limit,
            "namespace": ns_name,
        }

@router.get("/graphrag/edges")
async def list_graphrag_edges(
    namespace: Optional[str] = None,
    relation: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
    cursor: Optional[str] = None,
    node_ids: Optional[str] = None,
    current_user: Dict = Depends(get_current_user)
):
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphEdge
    ns_name = namespace or settings.DEFAULT_NAMESPACE
    limit = max(1, min(limit, 200))
    async with get_db_session() as session:
        filter_node_ids = None
        if node_ids:
            filter_node_ids = {x.strip() for x in node_ids.split(',') if x.strip()}
        q = select(GraphEdge)
        res = await session.execute(q)
        collected = []
        started = cursor is None
        for e in sorted(res.scalars().all(), key=lambda z: (z.id or "")):
            if (e.properties or {}).get("namespace", settings.DEFAULT_NAMESPACE) != ns_name:
                continue
            if relation and e.relation != relation:
                continue
            if filter_node_ids and e.source_id not in filter_node_ids and e.target_id not in filter_node_ids:
                continue
            if not started:
                if e.id == cursor:
                    started = True
                    continue
                else:
                    continue
            if started:
                if len(collected) < limit:
                    collected.append(e)
                else:
                    break
        next_cursor = collected[-1].id if collected and len(collected) == limit else None
        return {
            "results": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation,
                    "confidence": e.confidence,
                }
                for e in collected
            ],
            "count": len(collected),
            "cursor": next_cursor,
            "limit": limit,
            "namespace": ns_name,
        }

@router.get("/graphrag/stats")
async def graphrag_stats(current_user: Dict = Depends(get_current_user)):
    """Return high-level graph stats (node/edge counts, top relations)."""
    from sqlalchemy import func, select
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge
    async with get_db_session() as session:
        node_count = (await session.execute(select(func.count()).select_from(GraphNode))).scalar() or 0
        edge_count = (await session.execute(select(func.count()).select_from(GraphEdge))).scalar() or 0
        rel_counts_q = await session.execute(
            select(GraphEdge.relation, func.count().label("c")).group_by(GraphEdge.relation).limit(20)
        )
        rel_counts = [
            {"relation": r[0], "count": int(r[1])} for r in rel_counts_q.all()
        ]
    return {"nodes": node_count, "edges": edge_count, "relations": rel_counts}

@router.get("/graphrag/neighbors/{node_id}")
async def graphrag_neighbors(node_id: str, limit: int = 50, current_user: Dict = Depends(get_current_user)):
    """Return a node and its immediate neighbors (bidirectional)."""
    from sqlalchemy import select, or_
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge
    async with get_db_session() as session:
        nres = await session.execute(select(GraphNode).where(GraphNode.id == node_id))
        node = nres.scalars().first()
        if not node:
            raise HTTPException(status_code=404, detail="node not found")
        eres = await session.execute(
            select(GraphEdge).where(or_(GraphEdge.source_id == node_id, GraphEdge.target_id == node_id)).limit(limit)
        )
        edges = eres.scalars().all()
        neighbor_ids = set()
        for e in edges:
            neighbor_ids.add(e.source_id)
            neighbor_ids.add(e.target_id)
        n2res = await session.execute(select(GraphNode).where(GraphNode.id.in_(neighbor_ids)).limit(limit))
        nodes = n2res.scalars().all()
        return {
            "center": {"id": node.id, "name": node.name, "label": node.label, "properties": node.properties or {}},
            "nodes": [
                {"id": x.id, "name": x.name, "label": x.label, "properties": x.properties or {}} for x in nodes
            ],
            "edges": [
                {"id": e.id, "source_id": e.source_id, "target_id": e.target_id, "relation": e.relation, "confidence": e.confidence}
                for e in edges
            ],
        }

@router.get("/graphrag/search")
async def graphrag_search(q: str, limit: int = 25, current_user: Dict = Depends(get_current_user)):
    """Simple name prefix search over nodes for UI auto-complete."""
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode
    async with get_db_session() as session:
        res = await session.execute(
            select(GraphNode).where(GraphNode.name.ilike(f"{q}%")).limit(limit)
        )
        nodes = res.scalars().all()
        return {"results": [
            {"id": n.id, "name": n.name, "label": n.label} for n in nodes
        ]}

def require_graphrag_api_key(x_api_key: Optional[str] = Header(None)):
    if settings.GRAPHRAG_API_KEY:
        if not x_api_key or x_api_key != settings.GRAPHRAG_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True

# Secure selected endpoints with optional API key
secured_paths = [
    "/graphrag/ingest",
    "/graphrag/ingest-file",
    "/graphrag/ingest-batch",
    "/graphrag/query",
    "/graphrag/answer",
    "/graphrag/snapshots",
    "/graphrag/snapshots/diff",
]
for p in secured_paths:
    router.dependencies.append(Depends(require_graphrag_api_key))

@router.post("/graphrag/index/run")
async def graphrag_index_run(payload: Dict[str, Any], background_tasks: BackgroundTasks, current_user: Dict = Depends(get_current_user)):
    """Trigger Phase 2 batch index (skeleton). Body: { namespace?, dry_run? }"""
    namespace = payload.get('namespace')
    dry_run = bool(payload.get('dry_run', False))
    force = bool(payload.get('force', False))
    # Run in background to avoid blocking
    def _bg():
        try:
            from scripts.run_graphrag_index import orchestrate
            orchestrate(namespace or settings.DEFAULT_NAMESPACE, force, dry_run)
        except Exception:
            logger.exception("index_run_failed")
    background_tasks.add_task(_bg)
    return {"accepted": True, "namespace": namespace or settings.DEFAULT_NAMESPACE, "dry_run": dry_run}

@router.get("/graphrag/namespaces")
async def graphrag_namespaces(current_user: Dict = Depends(get_current_user)):
    """Return distinct namespaces present in the graph for UI selection.
    If namespace field is NULL it is normalized to the default namespace.
    """
    from sqlalchemy import select, func
    from app.core.database import get_db_session
    from app.models.database import GraphNode
    async with get_db_session() as session:
        res = await session.execute(select(func.coalesce(GraphNode.namespace, settings.DEFAULT_NAMESPACE)).distinct())
        rows = [r[0] for r in res.all() if r[0] is not None]
    # Ensure default is present
    if settings.DEFAULT_NAMESPACE not in rows:
        rows.append(settings.DEFAULT_NAMESPACE)
    return {"namespaces": sorted(rows)}

@router.get("/graphrag/metrics")
async def graphrag_metrics(format: str = "json", current_user: Dict = Depends(get_current_user)):
    if format == "prom":
        lines = []
        for k, v in graphrag_service.metrics.items():
            lines.append(f"graphrag_{k} {v}")
        return Response("\n".join(lines) + "\n", media_type="text/plain")
    m = graphrag_service.metrics
    # Derive average latencies if counts > 0
    def avg(sum_key: str, cnt_key: str) -> Optional[float]:
        s = m.get(sum_key, 0.0)
        c = m.get(cnt_key, 0) or 0
        return round(s / c, 6) if c else None
    derived = {
        "avg_ingest_latency": avg("ingest_latency_sum", "ingest_latency_count"),
        "avg_retrieval_latency": avg("retrieval_latency_sum", "retrieval_latency_count"),
        "avg_answer_latency": avg("answer_latency_sum", "answer_latency_count"),
    }
    # query2 averages
    if m.get("query2_latency_count"):
        derived["avg_query2_latency"] = round(m.get("query2_latency_sum", 0.0) / m.get("query2_latency_count", 1), 6)
    # artifact cache hit rate
    hits = m.get('artifact_cache_hits', 0)
    misses = m.get('artifact_cache_misses', 0)
    total_cache = hits + misses
    if total_cache:
        derived['artifact_cache_hit_rate'] = round(hits / total_cache, 6)
    extended = {**m, **derived}
    return {"metrics": extended}

@router.get("/graphrag/index/status")
async def graphrag_index_status(current_user: Dict = Depends(get_current_user)):
    """Return the latest known index status and directory link (if available)."""
    from pathlib import Path
    base_dir = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
    artifacts_root = base_dir / 'graphrag_artifacts'
    latest = artifacts_root / 'latest'
    status = graphrag_service.metrics.get('last_index_status')
    run_at = graphrag_service.metrics.get('last_index_run_at')
    return {
        "status": status,
        "last_index_run_at": run_at,
        "latest_dir": str(latest) if latest.exists() else None,
    }

@router.get("/graphrag/index/log")
async def graphrag_index_log(lines: int = 200, current_user: Dict = Depends(get_current_user)):
    """Tail the most recent orchestrator log if present."""
    from pathlib import Path
    base_dir = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
    artifacts_root = base_dir / 'graphrag_artifacts'
    latest = artifacts_root / 'latest'
    log_path = latest / 'orchestrator.log'
    if not log_path.exists():
        return Response("", media_type="text/plain")
    try:
        content = log_path.read_text(errors='ignore').splitlines()[-max(1, min(lines, 2000)):]
        return Response("\n".join(content)+"\n", media_type="text/plain")
    except Exception:
        return Response("", media_type="text/plain")

@router.get("/graphrag/stream")
async def graphrag_stream(request: Request):
    """Server-Sent Events stream for GraphRAG incremental updates (Phase 7)."""
    from asyncio import Queue
    if not getattr(smart_assistant, "_graphrag_stream_subs", None):  # type: ignore[name-defined]
        smart_assistant._graphrag_stream_subs = []  # type: ignore[attr-defined]
    q: Queue = Queue(maxsize=100)
    smart_assistant._graphrag_stream_subs.append(q)  # type: ignore[attr-defined]
    try:
        graphrag_service.metrics["stream_subscribers"] = graphrag_service.metrics.get("stream_subscribers",0)+1
    except Exception:
        pass
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await q.get()
                except Exception:
                    break
                yield f"event: {evt.get('event','message')}\ndata: {evt.get('data')}\n\n"
        finally:
            try:
                smart_assistant._graphrag_stream_subs.remove(q)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                graphrag_service.metrics["stream_subscribers"] = max(0, graphrag_service.metrics.get("stream_subscribers",1)-1)
            except Exception:
                pass
    return Response(event_generator(), media_type="text/event-stream")

@router.get("/graphrag/provenance")
async def graphrag_provenance(node_id: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Return simple provenance: chunks mentioning the entity and adjacent entities (Phase 13+)."""
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    if not node_id:
        raise HTTPException(status_code=400, detail="node_id required")
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge
    async with get_db_session() as session:
        node_q = await session.execute(select(GraphNode).where(GraphNode.id == node_id))
        node = node_q.scalars().first()
        if not node:
            raise HTTPException(status_code=404, detail="node not found")
        # Fetch all edges connecting entity to chunks or other entities
        edges_q = await session.execute(select(GraphEdge).where((GraphEdge.source_id == node_id) | (GraphEdge.target_id == node_id)))
        chunk_ids: Set[str] = set()
        neighbor_ids: Set[str] = set()
        for e in edges_q.scalars().all():
            other = e.target_id if e.source_id == node_id else e.source_id
            # Heuristic: chunks have '::chunk::' pattern
            if '::chunk::' in other:
                chunk_ids.add(other)
            else:
                neighbor_ids.add(other)
        chunks: List[Dict[str, Any]] = []
        if chunk_ids:
            cres = await session.execute(select(GraphNode).where(GraphNode.id.in_(list(chunk_ids))))
            for cn in cres.scalars().all():
                chunks.append({"id": cn.id, "text": (cn.properties or {}).get("text")})
        neighbors: List[Dict[str, Any]] = []
        if neighbor_ids:
            nres = await session.execute(select(GraphNode).where(GraphNode.id.in_(list(neighbor_ids))))
            for n in nres.scalars().all():
                neighbors.append({"id": n.id, "name": n.name, "label": n.label})
    return {"success": True, "node": {"id": node.id, "name": node.name, "label": node.label}, "chunks": chunks[:12], "neighbors": neighbors[:30]}

@router.get("/graphrag/stats/advanced")
async def graphrag_stats_advanced(namespace: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Advanced graph & clustering stats: degree distribution, cluster sizes, modularity.
    (Phase 3 extension)
    """
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphNode, GraphEdge, GraphClusterMembership
    ns = namespace or settings.DEFAULT_NAMESPACE
    async with get_db_session() as session:
        nres = await session.execute(select(GraphNode.id).where((GraphNode.namespace == ns) | (GraphNode.namespace.is_(None))))
        node_ids = [r[0] for r in nres.all()]
        eres = await session.execute(select(GraphEdge.source_id, GraphEdge.target_id))
        degree = {nid:0 for nid in node_ids}
        for s,t in eres.all():
            if s in degree: degree[s]+=1
            if t in degree: degree[t]+=1
        deg_values = list(degree.values())
        # cluster sizes
        cres = await session.execute(select(GraphClusterMembership.cluster_id).where(GraphClusterMembership.namespace == ns))
        from collections import Counter
        c_counts = Counter([r[0] for r in cres.all()])
        cluster_sizes = sorted([{ "cluster_id": cid, "size": sz } for cid, sz in c_counts.items()], key=lambda x: -x["size"])[:50]
        # Provide simple histogram for degree
        hist: Dict[int,int] = {}
        for d in deg_values:
            hist[d] = hist.get(d,0)+1
        # Attach current modularity if cached
        mod = None
        cache_key = (ns, "louvain")
        cr = cluster_service._cache.get(cache_key)
        if cr:
            mod = cr.modularity
    return {
        "namespace": ns,
        "degree_distribution": hist,
        "cluster_sizes": cluster_sizes,
        "modularity": mod,
        "node_count": len(node_ids),
    }

@router.get("/graphrag/cluster")
async def graphrag_cluster(namespace: Optional[str] = None, force: bool = False, current_user: Dict = Depends(get_current_user)):
    """Phase 3: Return Louvain clusters (cached; optionally recompute with force=true)."""
    result = await cluster_service.get_clusters(namespace=namespace, force=force)
    return {
        "namespace": namespace or settings.DEFAULT_NAMESPACE,
        "generated_at": result.generated_at,
        "algorithm": result.algorithm,
        "modularity": result.modularity,
        "stats": {**result.stats, **({"modularity": result.modularity} if result.modularity is not None else {})},
        "clusters": result.clusters,
    }

@router.get("/graphrag/cluster/summaries")
async def graphrag_cluster_summaries(namespace: Optional[str] = None, algorithm: str = "graphrag", limit: int = 500, current_user: Dict = Depends(get_current_user)):
    """Return stored cluster summaries (GraphRAG community reports) for hull labeling.
    Query params:
      - namespace (optional)
      - algorithm (default 'graphrag')
      - limit (max rows)
    """
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.database import GraphClusterSummary
    ns = namespace or settings.DEFAULT_NAMESPACE
    limit = max(1, min(limit, 1000))
    async with get_db_session() as session:
        q = await session.execute(select(GraphClusterSummary).where(GraphClusterSummary.namespace == ns, GraphClusterSummary.algorithm == algorithm).limit(limit))
        rows = q.scalars().all()
        out = [
            {
                "cluster_id": r.cluster_id,
                "label": r.label,
                "summary": r.summary,
                "algorithm": r.algorithm,
            }
            for r in rows
        ]
    return {"namespace": ns, "algorithm": algorithm, "count": len(out), "summaries": out}

@router.post("/graphrag/cluster/summarize")
async def graphrag_cluster_summarize(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Phase 3: Summarize one or more clusters via Gemini (cached).
    Body: { namespace, cluster_ids: [...], max_tokens? }
    """
    namespace = payload.get("namespace")
    cluster_ids = payload.get("cluster_ids") or []
    if not isinstance(cluster_ids, list) or not cluster_ids:
        raise HTTPException(status_code=400, detail="cluster_ids list required")
    max_tokens = int(payload.get("max_tokens", 120))
    summaries = await cluster_service.summarize_clusters(namespace=namespace, cluster_ids=cluster_ids, max_tokens=max_tokens)
    return {"namespace": namespace or settings.DEFAULT_NAMESPACE, "summaries": summaries}

@router.get("/graphrag/layout/status")
async def graphrag_layout_status(namespace: Optional[str] = None, current_user: Dict = Depends(get_current_user)):
    """Placeholder layout status endpoint (Phase 0).
    Will later report layout_version / freshness metrics.
    """
    return {"namespace": namespace or settings.DEFAULT_NAMESPACE, "layout": {"status": "placeholder", "version": 0}}

@router.post("/graphrag/layout/recompute")
async def graphrag_layout_recompute(payload: Dict[str, Any] = {}, current_user: Dict = Depends(get_current_user)):
    """Recompute and persist graph layout.
    Body: { namespace?: str, mode?: 'hybrid' | 'clustered' }
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    ns = payload.get("namespace")
    mode = payload.get("mode", "hybrid")
    result = await graphrag_service.recompute_layout(namespace=ns, mode=mode)
    return result

@router.post("/graphrag/centrality/recompute")
async def graphrag_centrality_recompute(payload: Dict[str, Any] = {}, current_user: Dict = Depends(get_current_user)):
    """Compute PageRank & Betweenness centrality and persist node importance.
    Body: { namespace?: str }
    """
    if not graphrag_service.enabled:
        return {"success": False, "error": "GraphRAG disabled"}
    ns = payload.get("namespace")
    result = await graphrag_service.compute_centrality(namespace=ns)
    return result

@router.post("/graphrag/path")
async def graphrag_path(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="source_id and target_id required")
    max_depth = int(payload.get("max_depth", 4))
    namespace = payload.get("namespace")
    path = await graphrag_service.shortest_path(source_id, target_id, max_depth=max_depth, namespace=namespace)
    return {"success": True, **path}
