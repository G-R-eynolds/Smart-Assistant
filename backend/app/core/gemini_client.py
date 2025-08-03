"""
Gemini AI Client for Smart Assistant

Handles integration with Google's Gemini API for cover letter generation
and other AI-powered features.
"""

import logging
from typing import Dict, Any, Optional
import aiohttp
import json
import structlog
from datetime import datetime

from app.core.config import settings
from app.core.cv_manager import cv_manager

logger = structlog.get_logger()


class GeminiClient:
    """
    Client for interacting with Google's Gemini API.
    """
    
    def __init__(self):
        """Initialize the Gemini client with configuration from settings."""
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.api_key:
            logger.warning("Gemini API key not configured")
    
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return bool(self.api_key)
    
    async def extract_job_search_keywords(
        self, 
        user_query: str
    ) -> Dict[str, Any]:
        """
        Extract optimized job search keywords from a natural language query.
        
        Args:
            user_query: The user's natural language job search request
            
        Returns:
            Dictionary with extracted keywords and search parameters
        """
        if not self.is_configured():
            # Fallback to simple keyword extraction if Gemini not configured
            return {
                "success": True,
                "keywords": user_query,
                "location": "",
                "job_type": "",
                "experience_level": "",
                "fallback_used": True
            }
        
        prompt = f"""
You are an expert job search assistant. Extract clean, focused search parameters from this job search query.

User Query: "{user_query}"

Extract the most effective LinkedIn search terms. Focus on:

1. **Keywords**: Essential job titles, skills, and technologies that would appear in job postings
2. **Location**: City, state, country, or "remote" if mentioned
3. **Job Type**: Full-time, Part-time, Contract, Freelance (only if explicitly mentioned)
4. **Experience Level**: Entry, Mid, Senior, Executive (only if clearly stated)

**Rules:**
- Keep keywords concise and focused (3-6 key terms max)
- Use terms that recruiters actually search for
- Don't over-specify - broader searches find more opportunities
- Only extract location/level/type if explicitly mentioned in the query

**Response Format (JSON only):**
{{
    "keywords": "concise search terms",
    "location": "location or empty string",
    "job_type": "type or empty string", 
    "experience_level": "level or empty string",
    "reasoning": "brief explanation"
}}

**Examples:**
- "Find me remote Python jobs" → {{"keywords": "python developer", "location": "remote", "job_type": "", "experience_level": "", "reasoning": "Focus on Python with developer role, remote specified"}}
- "Senior software engineer in London" → {{"keywords": "software engineer", "location": "London", "job_type": "", "experience_level": "Senior", "reasoning": "Core SE role with clear seniority and location"}}
- "Data scientist positions" → {{"keywords": "data scientist", "location": "", "job_type": "", "experience_level": "", "reasoning": "Simple, focused search term"}}

Extract now:
"""

        try:
            # Call Gemini API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/models/{self.model}:generateContent"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                params = {
                    "key": self.api_key
                }
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,  # Very low temperature for consistent JSON
                        "maxOutputTokens": 500,
                    }
                }
                
                async with session.post(url, headers=headers, params=params, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if "candidates" in result and len(result["candidates"]) > 0:
                            content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                            
                            # Try to extract JSON from the response
                            import json
                            import re
                            
                            # Remove any markdown formatting
                            content = re.sub(r'```json\s*', '', content)
                            content = re.sub(r'\s*```', '', content)
                            
                            # Try to find JSON object
                            json_match = re.search(r'(\{[^}]*"keywords"[^}]*\})', content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                            else:
                                # Try parsing the whole content as JSON
                                json_str = content
                            
                            try:
                                extracted_data = json.loads(json_str)
                                
                                # Validate required fields
                                result_data = {
                                    "success": True,
                                    "keywords": extracted_data.get("keywords", user_query),
                                    "location": extracted_data.get("location", ""),
                                    "job_type": extracted_data.get("job_type", ""),
                                    "experience_level": extracted_data.get("experience_level", ""),
                                    "reasoning": extracted_data.get("reasoning", ""),
                                    "search_strategy": extracted_data.get("search_strategy", ""),
                                    "original_query": user_query,
                                    "fallback_used": False
                                }
                                
                                logger.info(f"Successfully extracted keywords: {result_data['keywords']}")
                                return result_data
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON from Gemini response: {e}")
                                logger.debug(f"Raw response: {content}")
                                logger.debug(f"Attempted JSON: {json_str}")
                                
                                # Try a more lenient approach - extract fields manually
                                fallback_result = self._extract_fields_manually(content, user_query)
                                if fallback_result:
                                    return fallback_result
                                    
                                raise ValueError(f"Invalid JSON in response: {e}")
                        else:
                            raise ValueError("No content in Gemini response")
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini API error {response.status}: {error_text}")
                        raise Exception(f"Gemini API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            # Fallback to simple keyword extraction
            return {
                "success": False,
                "error": str(e),
                "keywords": user_query,  # Use original query as fallback
                "location": "",
                "job_type": "",
                "experience_level": "",
                "reasoning": "AI extraction failed, using original query",
                "search_strategy": "Manual keyword optimization recommended",
                "original_query": user_query,
                "fallback_used": True
            }
    
    def _extract_fields_manually(self, content: str, user_query: str) -> Optional[Dict[str, Any]]:
        """
        Fallback method to extract fields manually from response text.
        """
        try:
            import re
            
            # Try to extract keywords
            keywords_match = re.search(r'"?keywords"?\s*:\s*"([^"]*)"', content, re.IGNORECASE)
            keywords = keywords_match.group(1) if keywords_match else user_query
            
            # Try to extract location
            location_match = re.search(r'"?location"?\s*:\s*"([^"]*)"', content, re.IGNORECASE)
            location = location_match.group(1) if location_match else ""
            
            # Try to extract experience level
            exp_match = re.search(r'"?experience_level"?\s*:\s*"([^"]*)"', content, re.IGNORECASE)
            experience_level = exp_match.group(1) if exp_match else ""
            
            # Try to extract job type
            job_type_match = re.search(r'"?job_type"?\s*:\s*"([^"]*)"', content, re.IGNORECASE)
            job_type = job_type_match.group(1) if job_type_match else ""
            
            logger.info(f"Manual extraction successful: keywords={keywords}")
            
            return {
                "success": True,
                "keywords": keywords,
                "location": location,
                "job_type": job_type,
                "experience_level": experience_level,
                "reasoning": "Extracted manually from AI response",
                "search_strategy": "Manual parsing fallback used",
                "original_query": user_query,
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Manual extraction failed: {e}")
            return None

    async def generate_cover_letter(
        self, 
        job_title: str, 
        company: str, 
        job_description: str,
        cv_text: Optional[str] = None,
        style_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a cover letter using Gemini API.
        
        Args:
            job_title: The job title to apply for
            company: The company name
            job_description: The full job description
            cv_text: The user's CV content (defaults to CV from PDF)
            style_prompt: Custom style instructions (defaults to settings.COVER_LETTER_STYLE_PROMPT)
            
        Returns:
            Dictionary with success status and generated cover letter
        """
        if not self.is_configured():
            raise Exception("Gemini API is not properly configured")
        
        # Get CV content from CV manager if not provided
        if cv_text is None:
            cv_text = cv_manager.get_cv_text()
            if cv_text is None:
                logger.error("No CV content available - PDF not found or couldn't be processed")
                return {
                    "success": False,
                    "error": "CV not available",
                    "message": "Please upload your CV as a PDF file to generate cover letters"
                }
        
        cv_content = cv_text
        style_instructions = style_prompt or settings.COVER_LETTER_STYLE_PROMPT
        
        # Construct the prompt
        prompt = f"""
You are an expert career advisor and professional writer. Generate a personalized cover letter based on the following information:

**Job Details:**
- Position: {job_title}
- Company: {company}
- Job Description: {job_description}

**Candidate's CV:**
{cv_content}

**Style Guidelines:**
{style_instructions}

**Instructions:**
1. Analyze the job requirements and match them with the candidate's experience
2. Write a compelling cover letter that highlights relevant skills and achievements
3. Personalize it for the specific company and role
4. Include a strong opening and closing
5. Keep it professional and engaging
6. Do not include placeholder text like [Your Name] or [Date] - write the actual content

Please generate the cover letter now:
"""

        try:
            # Call Gemini API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/models/{self.model}:generateContent"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                # Gemini API request format
                data = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1024,
                    }
                }
                
                params = {"key": self.api_key}
                
                async with session.post(url, headers=headers, json=data, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract generated text from Gemini response
                        if "candidates" in result and len(result["candidates"]) > 0:
                            candidate = result["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                generated_text = candidate["content"]["parts"][0]["text"]
                                
                                logger.info(f"Successfully generated cover letter for {job_title} at {company}")
                                
                                return {
                                    "success": True,
                                    "cover_letter": generated_text.strip(),
                                    "generated_at": datetime.now().isoformat(),
                                    "job_title": job_title,
                                    "company": company
                                }
                        
                        # If we get here, the response format was unexpected
                        logger.error(f"Unexpected Gemini API response format: {result}")
                        return {
                            "success": False,
                            "error": "Unexpected response format from Gemini API",
                            "cover_letter": ""
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini API error {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"Gemini API error: {response.status} - {error_text}",
                            "cover_letter": ""
                        }
                        
        except Exception as e:
            logger.error(f"Error generating cover letter with Gemini: {e}")
            return {
                "success": False,
                "error": f"Failed to generate cover letter: {str(e)}",
                "cover_letter": ""
            }
    
    async def analyze_job_posting(self, job_description: str, cv_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a job posting to extract key requirements and calculate relevance score against CV.
        
        Args:
            job_description: The job description text
            cv_text: The user's CV content (defaults to CV from PDF)
            
        Returns:
            Dictionary with extracted job information and relevance score
        """
        if not self.is_configured():
            raise Exception("Gemini API is not properly configured")
        
        # Get CV content if not provided
        if cv_text is None:
            cv_text = cv_manager.get_cv_text()
            if cv_text is None:
                logger.warning("No CV available for relevance scoring")
                cv_text = "CV not available"
        
        prompt = f"""
Analyze the following job posting and calculate relevance against the candidate's CV.

**Job Description:**
{job_description}

**Candidate's CV:**
{cv_text}

**Analysis Required:**
1. Extract key job information for database storage
2. Calculate relevance score (0.0 to 1.0) based on CV match
3. Provide match reasoning

**Return JSON with these exact keys:**
{{
    "salary_range": "salary info or empty string if not mentioned",
    "education_requirements": "education requirements or empty string if not mentioned",
    "relevance_score": 0.85,
    "match_reasoning": "Detailed explanation of why this score was given"
}}

**Scoring Guidelines:**
- 0.9-1.0: Excellent match (90%+ requirements met, strong experience alignment)
- 0.8-0.89: Very good match (80-89% requirements met, good experience fit)
- 0.7-0.79: Good match (70-79% requirements met, adequate experience)
- 0.6-0.69: Fair match (60-69% requirements met, some gaps)
- 0.5-0.59: Poor match (50-59% requirements met, significant gaps)
- 0.0-0.49: Very poor match (major misalignment)

Focus on extracting salary and education information accurately. If salary is mentioned as a range, include the full range. If education requirements are mentioned (degree, certifications, etc.), capture them clearly.

Analyze now:
"""

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/models/{self.model}:generateContent"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                data = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.3,  # Lower temperature for more structured output
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1024,
                    }
                }
                
                params = {"key": self.api_key}
                
                async with session.post(url, headers=headers, json=data, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if "candidates" in result and len(result["candidates"]) > 0:
                            candidate = result["candidates"][0]
                            if "content" in candidate and "parts" in candidate["content"]:
                                generated_text = candidate["content"]["parts"][0]["text"]
                                
                                # Try to parse as JSON
                                try:
                                    # Clean up the response (remove markdown code blocks if present)
                                    cleaned_text = generated_text.strip()
                                    if cleaned_text.startswith("```json"):
                                        cleaned_text = cleaned_text[7:]
                                    if cleaned_text.endswith("```"):
                                        cleaned_text = cleaned_text[:-3]
                                    
                                    analysis = json.loads(cleaned_text.strip())
                                    
                                    logger.info("Successfully analyzed job posting with Gemini")
                                    return {
                                        "success": True,
                                        "analysis": analysis
                                    }
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse Gemini analysis as JSON: {e}")
                                    return {
                                        "success": False,
                                        "error": f"Failed to parse analysis as JSON: {str(e)}",
                                        "raw_response": generated_text
                                    }
                        
                        return {
                            "success": False,
                            "error": "Unexpected response format from Gemini API"
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini API error {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"Gemini API error: {response.status} - {error_text}"
                        }
                        
        except Exception as e:
            logger.error(f"Error analyzing job posting with Gemini: {e}")
            return {
                "success": False,
                "error": f"Failed to analyze job posting: {str(e)}"
            }


# Global instance for use across the application
gemini_client = GeminiClient()
