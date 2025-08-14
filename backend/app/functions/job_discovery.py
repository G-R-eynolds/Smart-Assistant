"""
Smart Assistant Job Discovery Pipeline Function

Processes job search queries, extracts parameters using AI, and integrates with 
LinkedIn job search capabilities.
"""
import asyncio
import json
import re
import logging
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
        max_jobs: int = 20
        timeout_seconds: int = 30
        use_gemini_parsing: bool = True
        gemini_api_key: str = ""
        log_level: str = "INFO"
    
    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves()
        self.logger = structlog.get_logger()
        
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
            # Extract the latest message from the messages array
            messages = body.get("messages", [])
            
            if not messages:
                return body
            
            # Get the latest user message
            latest_message = messages[-1]
            
            # Skip if not a dictionary (malformed message)
            if not isinstance(latest_message, dict):
                return body
                
            # Skip system-generated messages and AI responses
            message_role = latest_message.get("role", "")
            message_content = latest_message.get("content", "")
            
            # Only process actual user messages, not system or assistant messages
            if message_role != "user":
                return body
                
            # Skip system-generated follow-up suggestions and tasks
            if (message_content.startswith("### Task:") or 
                message_content.startswith("### Follow-up") or
                "suggest" in message_content.lower() and "follow-up" in message_content.lower()):
                return body
            
            # Check if this is a job-related request
            if not self._contains_job_trigger(message_content):
                # Not a job-related request, pass through
                return body

            logger.info(
                "Processing job discovery request", 
                user_id=user.get("id") if isinstance(user, dict) and user else None,
                message_preview=message_content[:100],
                message_role=latest_message.get("role", "unknown")
            )
            
            # Extract job parameters
            search_params = await self._extract_job_parameters(message_content, user)
            
            # Get jobs based on parameters
            jobs = await self._discover_jobs(search_params)
            
            # Format response - fix the data structure issue
            response = self._format_job_response(jobs)
            
            # Replace the user's message with our job search results
            # This way Gemini will process our results instead of the original command
            if isinstance(latest_message, dict):
                latest_message["content"] = f"Please help me understand these job search results:\n\n{response}"
            
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
        
        Uses Gemini Flash for intelligent keyword extraction, with regex as fallback
        """
        if self.valves.use_gemini_parsing:
            try:
                # Use Gemini Flash for sophisticated parameter extraction
                from app.core.gemini_client import GeminiClient
                
                gemini_client = GeminiClient()
                
                if gemini_client.is_configured():
                    logger.info("Using Gemini Flash for job parameter extraction")
                    extracted_data = await gemini_client.extract_job_search_keywords(message)
                    
                    if extracted_data.get("success", True):  # Gemini extraction succeeded
                        # Convert to our expected format
                        return {
                            "role": extracted_data.get("keywords", message),
                            "location": extracted_data.get("location", ""),
                            "experience_level": self._map_experience_level(extracted_data.get("experience_level", "")),
                            "employment_type": self._map_employment_type(extracted_data.get("job_type", "")),
                            "query": message,
                            "extraction_method": "gemini",
                            "gemini_reasoning": extracted_data.get("reasoning", ""),
                            "original_extraction": extracted_data
                        }
                    else:
                        logger.warning(f"Gemini extraction failed: {extracted_data.get('error', 'Unknown error')}")
                        
                else:
                    logger.warning("Gemini not configured, falling back to regex extraction")
                    
            except Exception as e:
                logger.warning(f"Gemini extraction failed, falling back to regex: {e}")
                
        # Fall back to regex extraction
        logger.info("Using regex-based parameter extraction")
        return self._extract_with_regex(message)
    
    def _map_experience_level(self, gemini_level: str) -> str:
        """Map Gemini experience level to our format"""
        if not gemini_level:
            return "mid"
            
        level_lower = gemini_level.lower()
        if any(term in level_lower for term in ["entry", "junior", "graduate", "recent"]):
            return "entry"
        elif any(term in level_lower for term in ["senior", "lead", "principal", "staff"]):
            return "senior"
        else:
            return "mid"
    
    def _map_employment_type(self, gemini_type: str) -> str:
        """Map Gemini job type to our format"""
        if not gemini_type:
            return "full-time"
            
        type_lower = gemini_type.lower()
        if "part" in type_lower:
            return "part-time"
        elif "contract" in type_lower:
            return "contract"
        elif "intern" in type_lower:
            return "internship"
        elif "freelance" in type_lower:
            return "freelance"
        else:
            return "full-time"
    
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
    
    async def _discover_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Discovers jobs using the LinkedIn scraper and stores them in Airtable.
        """
        start_time = datetime.now().timestamp()
        scraper = None
        logger = self.logger.bind(
            function="job_discovery",
            query=search_params.get("query", ""),
            location=search_params.get("location", "")
        )
        
        try:
            from ..core.linkedin_scraper_v2 import LinkedInScraperV2
            from ..core.airtable_client import AirtableClient
            from ..core.job_deduplication import JobDeduplicationService
            from ..core.gemini_client import GeminiClient
            from ..core.database import init_db
            
            # Initialize database for deduplication
            await init_db()
            
            # Initialize services
            scraper = LinkedInScraperV2()
            dedup_service = JobDeduplicationService()
            gemini_client = GeminiClient()
            
            # Get already processed URLs for deduplication
            logger.info("Checking for duplicate job URLs")
            processed_urls = await dedup_service.get_processed_urls()
            
            # Perform job search
            logger.info("Starting LinkedIn job search", search_params=search_params)
            raw_jobs = await scraper.search_jobs(
                keywords=search_params.get("role", ""),
                location=search_params.get("location", ""),
                experience_level=search_params.get("experience_level"),
                job_type=search_params.get("employment_type"),
                date_posted=search_params.get("date_posted", "week"),
                limit=self.valves.max_jobs
            )
            
            if not raw_jobs:
                logger.warning("No jobs found from LinkedIn search")
                return []
            
            # Filter out duplicate URLs
            new_jobs = []
            for job in raw_jobs:
                job_url = job.get('url', '')
                if job_url and job_url not in processed_urls:
                    new_jobs.append(job)
                else:
                    logger.debug(f"Skipping duplicate job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
            
            logger.info(f"After deduplication: {len(new_jobs)} new jobs out of {len(raw_jobs)} total")
            
            # Analyze jobs against CV for relevance
            analyzed_jobs = []
            for i, job in enumerate(new_jobs, 1):
                job_title = job.get('title', 'Unknown Position')
                company = job.get('company', 'Unknown Company')
                description = job.get('description', '')
                
                logger.info(f"Analyzing job {i}/{len(new_jobs)}: {job_title} at {company}")
                
                try:
                    # Analyze job posting against CV
                    analysis = await gemini_client.analyze_job_posting(description)
                    
                    if analysis.get('success', False):
                        # Extract the actual analysis data from the nested structure
                        analysis_data = analysis.get('analysis', {})
                        relevance_score = analysis_data.get('relevance_score', 0.5)
                        match_reasoning = analysis_data.get('match_reasoning', 'Analysis completed')
                        
                        # Add analysis results to job data
                        job['relevance_score'] = relevance_score
                        job['match_reasoning'] = match_reasoning
                        job['salary_range'] = analysis_data.get('salary_range', '')
                        job['education_requirements'] = analysis_data.get('education_requirements', '')
                        job['cv_analyzed'] = True
                        
                        # Only include jobs with decent relevance (>= 0.6 by default)
                        min_relevance = search_params.get('min_relevance_score', 0.6)
                        if relevance_score >= min_relevance:
                            analyzed_jobs.append(job)
                            logger.info(f"✅ Included job (relevance: {relevance_score:.2f}): {job_title}")
                        else:
                            logger.info(f"❌ Excluded job (relevance: {relevance_score:.2f}): {job_title} - {match_reasoning}")
                    else:
                        # If analysis fails, include job with default relevance
                        job['relevance_score'] = 0.5
                        job['match_reasoning'] = 'Analysis failed, included for review'
                        job['cv_analyzed'] = False
                        analyzed_jobs.append(job)
                        logger.warning(f"⚠️ Analysis failed for {job_title}, including anyway")
                        
                except Exception as e:
                    logger.error(f"Error analyzing job {job_title}: {e}")
                    # Include job anyway with low relevance
                    job['relevance_score'] = 0.3
                    job['match_reasoning'] = f'Analysis error: {str(e)}'
                    job['cv_analyzed'] = False
                    analyzed_jobs.append(job)
            
            logger.info(f"After CV analysis: {len(analyzed_jobs)} suitable jobs")
            
            # Store new jobs in Airtable and mark URLs as processed
            if analyzed_jobs:
                try:
                    airtable_client = AirtableClient()
                    await airtable_client.add_jobs(analyzed_jobs)
                    logger.info(f"Stored {len(analyzed_jobs)} jobs in Airtable")
                    
                    # Mark URLs as processed
                    await dedup_service.add_processed_urls(analyzed_jobs)
                    logger.info(f"Marked {len(analyzed_jobs)} job URLs as processed")
                    
                except Exception as e:
                    logger.warning(f"Failed to store jobs or update processed URLs: {e}")
                    # Continue without storage - don't fail the whole operation
            
            logger.info(f"Job search completed", job_count=len(analyzed_jobs))
            return analyzed_jobs
            
        except Exception as e:
            logger.error(f"Job discovery error: {e}")
            return []
        finally:
            if scraper:
                try:
                    await scraper.close()
                except:
                    pass

    def _format_job_response(self, jobs: List[Dict[str, Any]]) -> str:
        """
        Format job results into a readable response for the chat interface
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            A formatted string response for display in the chat
        """
        if not jobs:
            return "I couldn't find any matching jobs at the moment. Try refining your search criteria."
        
        # Format the job results as markdown for nice display in chat
        response = "### 🔍 Job Search Results (CV-Analyzed)\n\n"
        
        # Add top 3 jobs with details
        for i, job in enumerate(jobs[:3]):
            title = job.get("title", "Unknown Position")
            company = job.get("company", "Unknown Company")
            location = job.get("location", "Unknown Location")
            url = job.get("url", job.get("job_url", "#"))
            relevance = job.get("relevance_score", 0)
            cv_analyzed = job.get("cv_analyzed", False)
            
            response += f"**{i+1}. [{title} at {company}]({url})**\n"
            response += f"📍 {location} | "
            response += f"🎯 {relevance*100:.0f}% CV Match"
            
            # Add CV analysis indicator
            if cv_analyzed:
                response += " ✅\n"
            else:
                response += " ⚠️\n"
            
            # Add CV match reasoning
            match_reasoning = job.get("match_reasoning")
            if match_reasoning:
                response += f"🧠 *{match_reasoning}*\n"
            
            # Add salary if available
            salary_range = job.get("salary_range")
            if salary_range:
                response += f"� {salary_range}\n"
            
            # Add education requirements if available
            education_requirements = job.get("education_requirements")
            if education_requirements:
                response += f"🎓 {education_requirements}\n"
            
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
        start_time = datetime.now().timestamp()
        
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
                "processing_time_ms": int((datetime.now().timestamp() - start_time) * 1000)
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
