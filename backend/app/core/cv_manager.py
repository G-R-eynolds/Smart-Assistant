"""
CV Manager for Smart Assistant

Handles CV storage, PDF extraction, and text processing for job applications.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import PyPDF2
import structlog
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()


class CVManager:
    """
    Manager for handling CV files and text extraction.
    """
    
    def __init__(self):
        """Initialize the CV manager with the configured CV directory."""
        self.cv_directory = Path(settings.CV_DIRECTORY)
        self.cv_file_path = self.cv_directory / settings.CV_FILENAME
        self._cached_cv_text = None
        self._cache_timestamp = None
        
        # Ensure CV directory exists
        self.cv_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"CV Manager initialized. Looking for CV at: {self.cv_file_path}")
    
    def cv_exists(self) -> bool:
        """Check if the CV file exists."""
        return self.cv_file_path.exists() and self.cv_file_path.is_file()
    
    def get_cv_info(self) -> Dict[str, Any]:
        """Get information about the current CV file."""
        if not self.cv_exists():
            return {
                "exists": False,
                "path": str(self.cv_file_path),
                "message": f"CV file not found at {self.cv_file_path}. Please add your CV as '{settings.CV_FILENAME}' in the '{settings.CV_DIRECTORY}' directory."
            }
        
        stat = self.cv_file_path.stat()
        return {
            "exists": True,
            "path": str(self.cv_file_path),
            "filename": self.cv_file_path.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "message": f"CV found: {self.cv_file_path.name} ({round(stat.st_size / (1024 * 1024), 2)} MB)"
        }
    
    def extract_text_from_pdf(self) -> Optional[str]:
        """
        Extract text from the CV PDF file.
        
        Returns:
            The extracted text content or None if extraction fails
        """
        if not self.cv_exists():
            logger.error(f"CV file not found at {self.cv_file_path}")
            return None
        
        try:
            with open(self.cv_file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():  # Only add non-empty pages
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                        continue
                
                if not text_content:
                    logger.error("No text could be extracted from the PDF")
                    return None
                
                # Join all pages with double newline
                full_text = "\n\n".join(text_content)
                
                # Clean up the text
                cleaned_text = self._clean_extracted_text(full_text)
                
                logger.info(f"Successfully extracted {len(cleaned_text)} characters from CV PDF")
                return cleaned_text
                
        except Exception as e:
            logger.error(f"Error extracting text from CV PDF: {e}")
            return None
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted PDF text.
        
        Args:
            text: Raw text from PDF extraction
            
        Returns:
            Cleaned text suitable for AI processing
        """
        # Remove excessive whitespace
        import re
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph separation)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove trailing/leading whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove any remaining excessive whitespace
        text = text.strip()
        
        return text
    
    def get_cv_text(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get the CV text content, using cache if available and recent.
        
        Args:
            force_refresh: If True, ignore cache and re-extract from PDF
            
        Returns:
            The CV text content or None if not available
        """
        # Check if we should use cached version
        if not force_refresh and self._cached_cv_text and self._cache_timestamp:
            # Check if CV file has been modified since cache
            if self.cv_exists():
                file_modified = datetime.fromtimestamp(self.cv_file_path.stat().st_mtime)
                if file_modified.timestamp() <= self._cache_timestamp:
                    logger.debug("Using cached CV text")
                    return self._cached_cv_text
        
        # Extract fresh text from PDF
        cv_text = self.extract_text_from_pdf()
        
        if cv_text:
            # Update cache
            self._cached_cv_text = cv_text
            self._cache_timestamp = datetime.now().timestamp()
            logger.info("CV text cached successfully")
        
        return cv_text
    
    def get_cv_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the CV content for verification.
        
        Returns:
            Dictionary with CV summary information
        """
        cv_text = self.get_cv_text()
        
        if not cv_text:
            return {
                "available": False,
                "message": "CV text not available"
            }
        
        # Basic text analysis
        lines = cv_text.split('\n')
        words = cv_text.split()
        
        # Try to extract some basic information
        first_few_lines = '\n'.join(lines[:5])
        
        return {
            "available": True,
            "character_count": len(cv_text),
            "word_count": len(words),
            "line_count": len(lines),
            "first_lines_preview": first_few_lines,
            "message": f"CV loaded successfully: {len(words)} words, {len(lines)} lines"
        }
    
    def update_cv_file(self, file_content: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Update the CV file with new content.
        
        Args:
            file_content: The binary content of the new CV file
            filename: Optional filename (defaults to configured filename)
            
        Returns:
            Dictionary with update status
        """
        try:
            # Use provided filename or default
            target_filename = filename or settings.CV_FILENAME
            target_path = self.cv_directory / target_filename
            
            # Backup existing file if it exists
            if target_path.exists():
                backup_path = self.cv_directory / f"{target_path.stem}_backup_{int(datetime.now().timestamp())}{target_path.suffix}"
                target_path.rename(backup_path)
                logger.info(f"Backed up existing CV to {backup_path}")
            
            # Write new file
            with open(target_path, 'wb') as f:
                f.write(file_content)
            
            # Clear cache
            self._cached_cv_text = None
            self._cache_timestamp = None
            
            logger.info(f"CV file updated successfully: {target_path}")
            
            # Verify the new file
            cv_info = self.get_cv_info()
            
            return {
                "success": True,
                "message": f"CV updated successfully: {target_filename}",
                "file_info": cv_info
            }
            
        except Exception as e:
            logger.error(f"Failed to update CV file: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update CV file: {str(e)}"
            }


# Global instance for use across the application
cv_manager = CVManager()
