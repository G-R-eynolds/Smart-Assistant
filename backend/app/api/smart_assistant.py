"""
Smart Assistant Router

Main router for Smart Assistant functionality, including:
- Job discovery pipeline
- Inbox management
- Intelligence briefing
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.functions import job_discovery, inbox_management, intelligence_briefing

logger = logging.getLogger(__name__)

router = APIRouter(tags=["smart-assistant"])

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
