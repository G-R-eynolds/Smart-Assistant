"""
Airtable Client for Smart Assistant

Handles integration with Airtable for storing job data and other records.
"""

import logging
from typing import List, Dict, Any, Optional
from pyairtable import Api
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class AirtableClient:
    """
    Client for interacting with Airtable API to store job data.
    """
    
    def __init__(self):
        """Initialize the Airtable client with configuration from settings."""
        if not settings.AIRTABLE_API_KEY:
            logger.warning("Airtable API key not configured")
            self.api = None
            return
            
        if not settings.AIRTABLE_BASE_ID:
            logger.warning("Airtable base ID not configured")
            self.api = None
            return
            
        if not settings.AIRTABLE_TABLE_NAME:
            logger.warning("Airtable table name not configured")
            self.api = None
            return
            
        try:
            self.api = Api(settings.AIRTABLE_API_KEY)
            self.table = self.api.table(settings.AIRTABLE_BASE_ID, settings.AIRTABLE_TABLE_NAME)
            logger.info("Airtable client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Airtable client: {e}")
            self.api = None
            self.table = None
    
    def is_configured(self) -> bool:
        """Check if Airtable is properly configured."""
        return self.api is not None and self.table is not None
    
    async def add_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add job records to Airtable.
        
        Args:
            jobs: List of job dictionaries to add to Airtable
            
        Returns:
            Dictionary with success status and details
        """
        if not self.is_configured():
            raise Exception("Airtable client is not properly configured")
        
        if not jobs:
            return {
                "success": True,
                "records_added": 0,
                "message": "No jobs to add"
            }
        
        try:
            # Prepare records for Airtable
            records = []
            for job in jobs:
                # Calculate days posted if possible
                days_posted = None
                if job.get("posted_at"):
                    try:
                        from datetime import datetime
                        posted_date = datetime.fromisoformat(job["posted_at"].replace('Z', '+00:00'))
                        current_date = datetime.now(posted_date.tzinfo)
                        days_posted = (current_date - posted_date).days
                    except Exception as e:
                        logger.warning(f"Could not calculate days posted: {e}")
                
                # Map job fields to Airtable fields based on the table schema
                record = {
                    "Job Title": job.get("title", ""),
                    "Company": job.get("company", ""),
                    "Location": job.get("location", ""),
                    "URL": job.get("url", ""),
                    "Description": job.get("description", "")[:1000],  # Limit description length
                }
                
                # Add date fields in proper format
                if job.get("posted_at"):
                    try:
                        from datetime import datetime
                        posted_date = datetime.fromisoformat(job["posted_at"].replace('Z', '+00:00'))
                        record["Posted Date"] = posted_date.strftime('%Y-%m-%d')
                    except Exception as e:
                        logger.warning(f"Could not format posted date: {e}")
                
                if job.get("scraped_at"):
                    try:
                        from datetime import datetime
                        scraped_date = datetime.fromisoformat(job["scraped_at"].replace('Z', '+00:00'))
                        record["Scraped Date"] = scraped_date.strftime('%Y-%m-%d')  # Use simple date format
                    except Exception as e:
                        logger.warning(f"Could not format scraped date: {e}")
                
                # Add optional fields if they exist in the schema
                if job.get("relevance_score"):
                    record["Relevance Score"] = float(job.get("relevance_score", 0.0))
                    
                if job.get("source"):
                    record["Source"] = job.get("source", "linkedin")
                    
                if job.get("id"):
                    record["Job ID"] = job.get("id", "")
                
                # Add cover letter if generated
                if job.get("cover_letter") and job["cover_letter"].get("success"):
                    record["Cover Letter"] = job["cover_letter"].get("cover_letter", "")
                
                # Add job analysis fields if available
                if job.get("job_analysis") and job["job_analysis"].get("success"):
                    analysis_data = job["job_analysis"].get("analysis", {})
                    record["Salary Range"] = analysis_data.get("salary_range", "")
                    record["Education Requirements"] = analysis_data.get("education_requirements", "")
                
                records.append(record)
                logger.debug(f"Successfully created record for job: {record['Job Title']}")
            
            logger.info(f"Prepared {len(records)} records for Airtable")
            
            # Batch create records in Airtable (max 10 at a time)
            batch_size = 10
            created_records = []
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                try:
                    batch_result = self.table.batch_create(batch)
                    if batch_result and isinstance(batch_result, list):
                        created_records.extend(batch_result)
                        logger.info(f"Added {len(batch_result)} job records to Airtable (batch {i//batch_size + 1})")
                    else:
                        logger.warning(f"Batch create returned unexpected result: {batch_result}")
                except Exception as batch_error:
                    logger.error(f"Error creating batch {i//batch_size + 1}: {batch_error}")
                    # Continue with next batch
                    continue
            
            logger.info(f"Successfully added {len(created_records)} job records to Airtable")
            
            # Return record IDs if available
            if created_records:
                result = {
                    "success": True,
                    "count": len(created_records),
                    "record_ids": [record.get("id") for record in created_records if record and "id" in record]
                }
                logger.info(f"Successfully added {len(created_records)} jobs to Airtable")
                return result
            else:
                logger.warning("No records were successfully created")
                return {
                    "success": False,
                    "count": 0,
                    "record_ids": [],
                    "error": "No records were successfully created"
                }
            
        except Exception as e:
            logger.error(f"Error adding jobs to Airtable: {e}")
            raise Exception(f"Failed to add jobs to Airtable: {str(e)}")
    
    async def get_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve job records from Airtable.
        
        Args:
            limit: Maximum number of records to retrieve
            
        Returns:
            List of job records from Airtable
        """
        if not self.is_configured():
            raise Exception("Airtable client is not properly configured")
        
        try:
            # Get records from Airtable
            if limit:
                records = self.table.all(max_records=limit)
            else:
                records = self.table.all()
            
            # Convert Airtable records to job format
            jobs = []
            for record in records:
                fields = record["fields"]
                job = {
                    "id": fields.get("Job ID", record["id"]),
                    "title": fields.get("Job Title", ""),
                    "company": fields.get("Company", ""),
                    "location": fields.get("Location", ""),
                    "url": fields.get("URL", ""),
                    "description": fields.get("Description", ""),
                    "source": fields.get("Source", "airtable"),
                    "posted_at": fields.get("Posted Date", ""),
                    "scraped_at": fields.get("Scraped Date", ""),
                    "relevance_score": fields.get("Relevance Score", 0.0),
                    "airtable_id": record["id"]
                }
                
                # Add AI insights if available
                if fields.get("Match Reasoning") or fields.get("Skills Match"):
                    job["ai_insights"] = {
                        "match_reasoning": fields.get("Match Reasoning", ""),
                        "skills_match": fields.get("Skills Match", "").split(", ") if fields.get("Skills Match") else [],
                        "experience_match": fields.get("Experience Match", False)
                    }
                
                jobs.append(job)
            
            logger.info(f"Retrieved {len(jobs)} job records from Airtable")
            return jobs
            
        except Exception as e:
            logger.error(f"Error retrieving jobs from Airtable: {e}")
            raise Exception(f"Failed to retrieve jobs from Airtable: {str(e)}")


# Global instance for use across the application
airtable_client = AirtableClient()
