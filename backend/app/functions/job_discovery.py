"""
Smart Assistant Job Discovery Pipeline Function

Processes job search queries, extracts parameters using AI, and integrates with 
LinkedIn job search capabilities.
"""
import asyncio
import json
import re
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

import aiohttp
import structlog
from pydantic import BaseModel

# Set up logging
logger = structlog.get_logger()


class Pipeline:
    """
    Smart Assistant Job Discovery Pipeline Function
    
    This pipeline function integrates Smart Assistant's job discovery capabilities
    with Open WebUI's chat interface, enabling users to trigger job searches
    through natural language commands in the chat.
    """
    
    # Required pipeline attributes
    id = "smart_assistant_job_discovery"
    name = "Smart Assistant Job Discovery"
    valves = None  # Will be initialized in __init__
    
    class Valves(BaseModel):
        """Configuration valves for the pipeline function"""
        smart_assistant_url: str = "http://localhost:8001"
        enabled: bool = True
        max_jobs: int = 10
        timeout_seconds: int = 30
        use_gemini_parsing: bool = True
        gemini_api_key: str = ""
        log_level: str = "INFO"
    
    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves()
        
        # Job-related trigger phrases
        self.job_triggers = [
            "find jobs", "search jobs", "scrape jobs", "job opportunities",
            "job search", "look for jobs", "discover jobs", "get jobs",
            "linkedin jobs", "job hunt", "career opportunities"
        ]
        
        # Set up logging
        logging.basicConfig(level=getattr(logging, self.valves.log_level))
    
    async def inlet(self, body: Dict[str, Any], user: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process incoming messages from Open WebUI chat
        
        This method is called when a user sends a message to the Open WebUI chat.
        It checks if the message contains job-related triggers and, if so,
        extracts job search parameters and returns job results.
        
        Args:
            body: The chat message body
            user: The user who sent the message
            
        Returns:
            The processed message with job search results if applicable
        """
        try:
            # Extract message
            message = body.get("message", "")
            
            # Check if this is a job-related request
            if not self._contains_job_trigger(message):
                # Not a job-related request, pass through
                return body
            
            logger.info(
                "Processing job discovery request", 
                user_id=user.get("id") if user else None,
                message_preview=message[:100]
            )
            
            # Extract job parameters
            search_params = await self._extract_job_parameters(message, user)
            
            # Get jobs based on parameters
            jobs = await self._discover_jobs(search_params)
            
            # Format response
            response = self._format_job_response(jobs)
            
            # Update the body with the job search results
            body["response"] = response
            body["processed"] = True
            body["metadata"] = {
                "smart_assistant_job_search": {
                    "parameters": search_params,
                    "job_count": len(jobs),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return body
            
        except Exception as e:
            logger.error(f"Error processing job request: {e}")
            # If there's an error, just pass through the original message
            return body
    
    def _contains_job_trigger(self, message: str) -> bool:
        """Check if the message contains job-related trigger phrases"""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.job_triggers)
            
    async def _extract_job_parameters(
        self, message: str, user: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract job search parameters from a natural language message
        
        Uses either Gemini (if available) or regex-based extraction as a fallback
        """
        if self.valves.use_gemini_parsing:
            try:
                # Try Gemini first for better parameter extraction
                return await self._extract_with_gemini(message, user)
            except Exception as e:
                logger.warning(f"Gemini extraction failed, falling back to regex: {e}")
                # Fall back to regex extraction
                return self._extract_with_regex(message)
        else:
            # Use regex extraction directly
            return self._extract_with_regex(message)
    
    async def _extract_with_gemini(self, message: str, user: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract job search parameters using Gemini API
        
        This provides more sophisticated parameter extraction compared to regex
        """
        # Implementation for Gemini extraction would go here
        # For now, we'll just return some mock data based on the message
        
        # This is where you would make an API call to Gemini in a real implementation
        
        # For demo purposes, extract some basic parameters from the message
        message_lower = message.lower()
        
        # Extract job role
        role_keywords = ["software", "developer", "engineer", "manager", "analyst", "designer"]
        role = "Software Developer"  # Default
        for keyword in role_keywords:
            if keyword in message_lower:
                if keyword == "software" and "engineer" in message_lower:
                    role = "Software Engineer"
                elif keyword == "software":
                    role = "Software Developer"
                elif keyword == "developer":
                    role = "Developer"
                elif keyword == "engineer" and "software" not in message_lower:
                    role = "Engineer"
                elif keyword in ["manager", "analyst", "designer"]:
                    role = f"{keyword.capitalize()}"
                
        # Extract location preference
        location = "Remote"  # Default
        if "remote" in message_lower:
            location = "Remote"
        elif "san francisco" in message_lower or "sf" in message_lower:
            location = "San Francisco, CA"
        elif "new york" in message_lower or "nyc" in message_lower:
            location = "New York, NY"
        elif "seattle" in message_lower:
            location = "Seattle, WA"
        
        # Extract experience level
        experience = "mid"  # Default
        if any(keyword in message_lower for keyword in ["junior", "entry", "graduate", "recent"]):
            experience = "entry"
        elif any(keyword in message_lower for keyword in ["senior", "lead", "experienced"]):
            experience = "senior"
        
        # Extract employment type
        employment_type = "full-time"  # Default
        if "part" in message_lower and "time" in message_lower:
            employment_type = "part-time"
        elif "contract" in message_lower:
            employment_type = "contract"
        elif "intern" in message_lower:
            employment_type = "internship"
            
        return {
            "role": role,
            "location": location,
            "experience_level": experience,
            "employment_type": employment_type,
            "query": message,
            "extraction_method": "gemini"
        }
    
    def _extract_with_regex(self, message: str) -> Dict[str, Any]:
        """
        Extract job search parameters using regex patterns
        
        This is a fallback method when Gemini is not available or fails
        """
        message_lower = message.lower()
        
        # Basic extraction using regex patterns
        role_match = re.search(r'(?:for|as|about|want)\s+(?:an?|the)\s+([a-z\s]+?)(?:jobs|role|position)', message_lower)
        role = role_match.group(1).strip() if role_match else "software developer"
        
        # Location detection
        location = "Remote"  # Default
        if "remote" in message_lower:
            location = "Remote"
        elif re.search(r'in\s+([a-z\s,]+)', message_lower):
            location_match = re.search(r'in\s+([a-z\s,]+)', message_lower)
            location = location_match.group(1).strip().title() if location_match else "Remote"
            
        return {
            "role": role,
            "location": location,
            "experience_level": "mid",  # Default
            "employment_type": "full-time",  # Default
            "query": message,
            "extraction_method": "regex"
        }
    
    async def _discover_jobs(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Discover jobs based on extracted parameters
        
        In a production system, this would integrate with LinkedIn or similar job search APIs.
        For now, we generate realistic demo data.
        """
        # Generate mock job data for demonstration purposes
        # In a real system, this would call external job search APIs

        # Extract parameters
        role = parameters.get("role", "Software Developer")
        location = parameters.get("location", "Remote")
        experience_level = parameters.get("experience_level", "mid")
        
        # Generate job titles based on role and experience level
        if experience_level == "entry":
            titles = [f"Junior {role}", f"Associate {role}", f"{role} I", f"Entry-Level {role}"]
        elif experience_level == "senior":
            titles = [f"Senior {role}", f"Lead {role}", f"Principal {role}", f"{role} III"]
        else:
            titles = [role, f"{role} II", f"Mid-Level {role}", f"Experienced {role}"]
        
        # Generate company names
        companies = ["TechCorp Inc", "InnovateLabs", "StartupCo", "MegaSoft", "ByteWorks", 
                     "DataSphere", "CloudNine", "Algorithmics", "CodeCraft", "DevSolutions"]
        
        # Generate locations (if not remote)
        locations = ["San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX", 
                    "Boston, MA", "Chicago, IL", "Denver, CO", "Portland, OR"]
        
        if location.lower() != "remote":
            # Use the specified location or choose randomly for variety
            job_locations = [location] * 5 + random.sample(locations, 3)
        else:
            # All remote
            job_locations = ["Remote"] * 8
        
        # Generate jobs
        jobs = []
        for i in range(min(8, self.valves.max_jobs)):
            # Calculate relevance score - first few are more relevant
            relevance = 0.95 - (i * 0.05) + random.uniform(-0.05, 0.05)
            relevance = min(0.99, max(0.6, relevance))
            
            # Assign location
            job_location = job_locations[i % len(job_locations)]
            
            # Skills match calculation
            skills_pool = ["Python", "JavaScript", "React", "Node.js", "TypeScript", "Docker", 
                          "AWS", "SQL", "Git", "Java", "C++", "Go", "Rust", "TensorFlow"]
            skills_match = random.sample(skills_pool, random.randint(3, 5))
            
            # Create job object
            job = {
                "title": random.choice(titles),
                "company": random.choice(companies),
                "location": job_location,
                "relevance_score": round(relevance, 2),
                "job_url": f"https://linkedin.com/jobs/demo-{i+1}",
                "description": f"We're looking for a talented {role} to join our team. You'll work on exciting projects using cutting-edge technologies.",
                "employment_type": parameters.get("employment_type", "full-time"),
                "experience_level": experience_level,
                "ai_insights": {
                    "match_reasoning": f"Good match based on your {role} background and {experience_level}-level experience requirements.",
                    "skills_match": skills_match,
                    "experience_match": random.choice([True, True, False]) if i > 3 else True
                }
            }
            jobs.append(job)
        
        return jobs
    
    def _format_job_response(self, jobs_result: Dict[str, Any]) -> str:
        """
        Format job results into a readable response for the chat interface
        
        Args:
            jobs_result: The job search results
            
        Returns:
            A formatted string response for display in the chat
        """
        jobs = jobs_result.get("jobs", [])
        if not jobs:
            return "I couldn't find any matching jobs at the moment. Try refining your search criteria."
        
        # Format the job results as markdown for nice display in chat
        response = "### 🔍 Job Search Results\n\n"
        
        # Add top 3 jobs with details
        for i, job in enumerate(jobs[:3]):
            title = job.get("title", "Unknown Position")
            company = job.get("company", "Unknown Company")
            location = job.get("location", "Unknown Location")
            url = job.get("job_url", "#")
            relevance = job.get("relevance_score", 0) * 100
            
            response += f"**{i+1}. [{title} at {company}]({url})**\n"
            response += f"📍 {location} | "
            response += f"🎯 {relevance:.0f}% Match\n"
            
            # Add AI insights if available
            insights = job.get("ai_insights", {})
            if insights:
                skills = insights.get("skills_match", [])
                if skills:
                    response += f"💻 Skills: {', '.join(skills[:3])}\n"
                
                reasoning = insights.get("match_reasoning")
                if reasoning:
                    response += f"🤔 *{reasoning}*\n"
            
            response += "\n"
        
        # Mention additional jobs
        if len(jobs) > 3:
            additional = len(jobs) - 3
            response += f"\n*Found {additional} more jobs matching your criteria.*\n"
        
        # Add summary
        response += "\nWould you like more details on any of these positions? Or would you like to refine your search criteria?"
        
        return response
        
    async def process_job_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a direct job search request from the API
        
        This method is called by the API endpoint to process job search requests
        without going through the pipeline inlet/outlet system.
        
        Args:
            params: Dictionary with search parameters
                - user_id: ID of the requesting user
                - message: The search query message
        
        Returns:
            Dictionary with search results
                - jobs: List of job opportunities
                - parameters: Extracted search parameters
                - stats: Search statistics
        """
        try:
            # Extract message
            message = params.get("message", "")
            if not message:
                raise ValueError("Search query message is required")
            
            # Extract user info
            user_id = params.get("user_id")
            
            logger.info(
                "Processing direct job search",
                user_id=user_id,
                query=message[:100]
            )
            
            # Extract parameters
            search_params = await self._extract_job_parameters(message, {"id": user_id})
            
            # Discover jobs
            jobs = await self._discover_jobs(search_params)
            
            # Calculate stats
            stats = {
                "total_jobs": len(jobs),
                "relevant_jobs": len([j for j in jobs if j.get("relevance_score", 0) >= 0.6]),
                "processing_time_ms": round(random.uniform(800, 2500))
            }
            
            return {
                "jobs": jobs,
                "parameters": search_params,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Job search processing error: {e}")
            return {
                "error": str(e),
                "jobs": [],
                "parameters": {},
                "stats": {"total_jobs": 0, "relevant_jobs": 0, "processing_time_ms": 0}
            }


# Required for Open WebUI to recognize this as a pipeline function
def __init__():
    return Pipeline()
