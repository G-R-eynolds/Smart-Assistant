"""
Job URL Deduplication Service

Provides fast URL-based deduplication for job processing using SQLite database.
This prevents processing the same job multiple times.
"""

import asyncio
from typing import List, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
import structlog

from app.models.database import ProcessedJobUrl
from app.core.database import get_async_session

logger = structlog.get_logger()


class JobDeduplicationService:
    """Service for tracking and filtering duplicate job URLs."""
    
    async def get_processed_urls(self) -> Set[str]:
        """
        Get all processed job URLs from the database.
        
        Returns:
            Set of URLs that have been processed
        """
        try:
            async with get_async_session() as session:
                stmt = select(ProcessedJobUrl.url)
                result = await session.execute(stmt)
                urls = {row[0] for row in result.fetchall()}
                
                logger.info(f"Retrieved {len(urls)} processed job URLs from database")
                return urls
                
        except Exception as e:
            logger.error(f"Error retrieving processed URLs: {e}")
            return set()
    
    async def add_processed_urls(self, jobs: List[Dict[str, Any]]) -> None:
        """
        Add job URLs to the processed URLs table.
        
        Args:
            jobs: List of job dictionaries that have been processed
        """
        if not jobs:
            return
        
        try:
            async with get_async_session() as session:
                # Prepare records for bulk insert
                records = []
                for job in jobs:
                    url = job.get("url")
                    if url:
                        records.append({
                            "url": url,
                            "job_title": job.get("title", "")[:100],  # Limit length
                            "company": job.get("company", "")[:100]   # Limit length
                        })
                
                if records:
                    # Use SQLite's INSERT OR IGNORE to handle duplicates gracefully
                    stmt = insert(ProcessedJobUrl).prefix_with("OR IGNORE")
                    await session.execute(stmt, records)
                    await session.commit()
                    
                    logger.info(f"Added {len(records)} job URLs to processed list")
                else:
                    logger.warning("No valid URLs found in jobs to add")
                    
        except Exception as e:
            logger.error(f"Error adding processed URLs: {e}")
    
    def filter_new_jobs(self, jobs: List[Dict[str, Any]], processed_urls: Set[str]) -> List[Dict[str, Any]]:
        """
        Filter out jobs that have already been processed based on URL.
        
        Args:
            jobs: List of job dictionaries
            processed_urls: Set of URLs that have been processed
            
        Returns:
            List of jobs that haven't been processed yet
        """
        if not jobs:
            return jobs
        
        new_jobs = []
        duplicate_count = 0
        
        for job in jobs:
            job_url = job.get("url", "")
            if job_url and job_url in processed_urls:
                duplicate_count += 1
                logger.debug(f"Skipping duplicate job: {job.get('title')} at {job.get('company')} - URL already processed")
            else:
                new_jobs.append(job)
        
        if duplicate_count > 0:
            logger.info(f"🔄 Filtered out {duplicate_count} duplicate jobs, {len(new_jobs)} new jobs to process")
        else:
            logger.info(f"✅ No duplicates found, all {len(new_jobs)} jobs are new")
        
        return new_jobs
    
    async def process_jobs_with_deduplication(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Complete deduplication workflow: get processed URLs, filter jobs, and track new ones.
        
        Args:
            jobs: List of job dictionaries from scraping
            
        Returns:
            List of new jobs that haven't been processed before
        """
        if not jobs:
            return jobs
        
        logger.info(f"🔍 Starting deduplication check for {len(jobs)} jobs")
        
        # Get already processed URLs
        processed_urls = await self.get_processed_urls()
        
        # Filter out duplicates
        new_jobs = self.filter_new_jobs(jobs, processed_urls)
        
        if new_jobs:
            logger.info(f"📝 Will process {len(new_jobs)} new jobs (filtered {len(jobs) - len(new_jobs)} duplicates)")
        else:
            logger.info("⚠️ All jobs were duplicates, nothing new to process")
        
        return new_jobs
    
    async def mark_jobs_as_processed(self, jobs: List[Dict[str, Any]]) -> None:
        """
        Mark jobs as processed after successful AI analysis and Airtable storage.
        
        Args:
            jobs: List of job dictionaries that have been successfully processed
        """
        await self.add_processed_urls(jobs)
        logger.info(f"✅ Marked {len(jobs)} jobs as processed")


# Global instance for use across the application
job_deduplication_service = JobDeduplicationService()
