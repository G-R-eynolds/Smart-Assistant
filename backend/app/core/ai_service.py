"""
AI Service Layer for Smart Assistant

Provides centralized AI capabilities using Google Gemini API for:
- Job relevance scoring and analysis
- CV/Resume tailoring and optimization
- Cover letter generation
- Content quality assessment
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
import structlog
from datetime import datetime

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.core.config import settings

logger = structlog.get_logger()


class AIService:
    """Centralized AI service using Google Gemini"""
    
    def __init__(self):
        self.model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Google Gemini with proper configuration"""
        if not settings.GOOGLE_GEMINI_API_KEY:
            logger.warning("Google Gemini API key not configured")
            return
            
        try:
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
            
            # Configure safety settings for business use
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Use the appropriate model based on task complexity
            self.model = genai.GenerativeModel(
                model_name=settings.DEFAULT_MODEL,
                safety_settings=safety_settings
            )
            
            self.premium_model = genai.GenerativeModel(
                model_name=settings.PREMIUM_MODEL,
                safety_settings=safety_settings
            )
            
            logger.info("Gemini AI service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            raise
    
    async def generate_content(self, prompt: str, use_premium: bool = False) -> Dict[str, Any]:
        """
        General content generation method for CV processing and other tasks
        
        Args:
            prompt: The prompt to send to the AI
            use_premium: Whether to use the premium model
            
        Returns:
            Dict with 'content' key containing the response text
        """
        if not self.model:
            logger.warning("AI model not available, returning empty response")
            return {"content": ""}
        
        try:
            model = self.premium_model if use_premium else self.model
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, model.generate_content, prompt
            )
            
            return {"content": response.text}
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return {"content": ""}
    
    async def analyze_job_relevance(
        self, 
        job_description: str, 
        user_profile: Dict[str, Any],
        use_premium: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze job relevance against user profile with detailed scoring
        
        Returns:
        {
            "relevance_score": float (0-1),
            "skills_match": Dict[str, float],
            "experience_match": float,
            "salary_alignment": float,
            "location_score": float,
            "reasoning": str,
            "recommendations": List[str]
        }
        """
        if not self.model:
            return self._fallback_job_scoring(job_description, user_profile)
        
        try:
            model = self.premium_model if use_premium else self.model
            
            prompt = self._build_job_analysis_prompt(job_description, user_profile)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, model.generate_content, prompt
            )
            
            # Parse structured response
            analysis = self._parse_job_analysis_response(response.text)
            
            logger.info(
                "Job relevance analyzed",
                job_title=job_description.get("title", "Unknown"),
                relevance_score=analysis.get("relevance_score", 0),
                user_id=user_profile.get("user_id")
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Job relevance analysis failed: {e}")
            return self._fallback_job_scoring(job_description, user_profile)
    
    async def generate_cv_content(
        self, 
        user_profile: Dict[str, Any],
        job_description: str,
        existing_cv: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate or tailor CV content for specific job application
        
        Returns:
        {
            "tailored_cv": str,
            "key_improvements": List[str],
            "skills_highlighted": List[str],
            "quality_score": float,
            "recommendations": List[str]
        }
        """
        if not self.model:
            return self._fallback_cv_generation(user_profile, job_description)
        
        try:
            prompt = self._build_cv_generation_prompt(
                user_profile, job_description, existing_cv
            )
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.premium_model.generate_content, prompt
            )
            
            cv_content = self._parse_cv_generation_response(response.text)
            
            logger.info(
                "CV content generated",
                user_id=user_profile.get("user_id"),
                quality_score=cv_content.get("quality_score", 0)
            )
            
            return cv_content
            
        except Exception as e:
            logger.error(f"CV generation failed: {e}")
            return self._fallback_cv_generation(user_profile, job_description)
    
    async def generate_cover_letter(
        self,
        user_profile: Dict[str, Any],
        job_description: str,
        company_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized cover letter for job application
        
        Returns:
        {
            "cover_letter": str,
            "tone": str,
            "key_points": List[str],
            "quality_score": float,
            "word_count": int
        }
        """
        if not self.model:
            return self._fallback_cover_letter_generation(user_profile, job_description)
        
        try:
            prompt = self._build_cover_letter_prompt(
                user_profile, job_description, company_info
            )
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.premium_model.generate_content, prompt
            )
            
            cover_letter = self._parse_cover_letter_response(response.text)
            
            logger.info(
                "Cover letter generated",
                user_id=user_profile.get("user_id"),
                word_count=cover_letter.get("word_count", 0)
            )
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return self._fallback_cover_letter_generation(user_profile, job_description)
    
    def _build_job_analysis_prompt(self, job_description: str, user_profile: Dict[str, Any]) -> str:
        """Build prompt for job relevance analysis"""
        return f"""
Analyze the job relevance for this candidate against the job posting. Provide a detailed analysis in JSON format.

USER PROFILE:
Name: {user_profile.get('full_name', 'Not provided')}
Skills: {', '.join(user_profile.get('skills', []))}
Experience Level: {user_profile.get('experience_level', 'Not specified')}
Previous Roles: {', '.join(user_profile.get('previous_roles', []))}
Education: {user_profile.get('education', 'Not provided')}
Career Goals: {user_profile.get('career_goals', 'Not specified')}
Salary Expectations: {user_profile.get('salary_expectation', 'Not specified')}
Location Preferences: {user_profile.get('location_preferences', [])}

JOB POSTING:
Title: {job_description.get('title', 'Not provided')}
Company: {job_description.get('company', 'Not provided')}
Description: {job_description.get('description', 'Not provided')}
Requirements: {job_description.get('requirements', 'Not provided')}
Salary Range: {job_description.get('salary_range', 'Not specified')}
Location: {job_description.get('location', 'Not specified')}
Employment Type: {job_description.get('employment_type', 'Not specified')}

Provide analysis in this exact JSON format:
{{
    "relevance_score": <float 0-1>,
    "skills_match": {{
        "technical_skills": <float 0-1>,
        "soft_skills": <float 0-1>,
        "missing_skills": ["skill1", "skill2"]
    }},
    "experience_match": <float 0-1>,
    "salary_alignment": <float 0-1>,
    "location_score": <float 0-1>,
    "reasoning": "<detailed explanation>",
    "recommendations": ["recommendation1", "recommendation2"]
}}
"""
    
    def _build_cv_generation_prompt(
        self, 
        user_profile: Dict[str, Any], 
        job_description: str,
        existing_cv: Optional[str] = None
    ) -> str:
        """Build prompt for CV generation/tailoring"""
        base_prompt = f"""
Generate a professional CV tailored specifically for this job application.

USER PROFILE:
{json.dumps(user_profile, indent=2)}

JOB POSTING:
{json.dumps(job_description, indent=2)}
"""
        
        if existing_cv:
            base_prompt += f"\nEXISTING CV:\n{existing_cv}\n"
            base_prompt += "\nTailor the existing CV to better match the job requirements."
        else:
            base_prompt += "\nGenerate a new professional CV from the user profile."
        
        base_prompt += """

Provide response in this JSON format:
{
    "tailored_cv": "<complete CV in markdown format>",
    "key_improvements": ["improvement1", "improvement2"],
    "skills_highlighted": ["skill1", "skill2"],
    "quality_score": <float 0-1>,
    "recommendations": ["rec1", "rec2"]
}
"""
        return base_prompt
    
    def _build_cover_letter_prompt(
        self,
        user_profile: Dict[str, Any],
        job_description: str,
        company_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for cover letter generation"""
        prompt = f"""
Write a compelling, personalized cover letter for this job application.

USER PROFILE:
{json.dumps(user_profile, indent=2)}

JOB POSTING:
{json.dumps(job_description, indent=2)}
"""
        
        if company_info:
            prompt += f"\nCOMPANY INFORMATION:\n{json.dumps(company_info, indent=2)}\n"
        
        prompt += """
Write a professional cover letter that:
1. Shows genuine interest in the role and company
2. Highlights relevant experience and skills
3. Demonstrates value proposition
4. Uses appropriate professional tone
5. Is concise but compelling (250-400 words)

Provide response in this JSON format:
{
    "cover_letter": "<complete cover letter text>",
    "tone": "<professional/enthusiastic/confident>",
    "key_points": ["point1", "point2"],
    "quality_score": <float 0-1>,
    "word_count": <integer>
}
"""
        return prompt
    
    def _parse_job_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate job analysis response"""
        try:
            # Extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            analysis = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['relevance_score', 'skills_match', 'experience_match']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = 0.5  # Default value
            
            # Ensure scores are within bounds
            analysis['relevance_score'] = max(0, min(1, analysis['relevance_score']))
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse job analysis response: {e}")
            return {
                "relevance_score": 0.5,
                "skills_match": {"technical_skills": 0.5, "soft_skills": 0.5},
                "experience_match": 0.5,
                "reasoning": "Analysis parsing failed",
                "recommendations": ["Review job requirements carefully"]
            }
    
    def _parse_cv_generation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate CV generation response"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            cv_data = json.loads(json_str)
            
            # Ensure required fields
            if 'tailored_cv' not in cv_data:
                cv_data['tailored_cv'] = "CV generation failed - please try again"
            
            if 'quality_score' not in cv_data:
                cv_data['quality_score'] = 0.5
            
            return cv_data
            
        except Exception as e:
            logger.error(f"Failed to parse CV generation response: {e}")
            return {
                "tailored_cv": "CV generation failed due to parsing error",
                "key_improvements": [],
                "quality_score": 0.0,
                "recommendations": ["Try regenerating the CV"]
            }
    
    def _parse_cover_letter_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate cover letter response"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            letter_data = json.loads(json_str)
            
            # Calculate word count if not provided
            if 'word_count' not in letter_data and 'cover_letter' in letter_data:
                letter_data['word_count'] = len(letter_data['cover_letter'].split())
            
            return letter_data
            
        except Exception as e:
            logger.error(f"Failed to parse cover letter response: {e}")
            return {
                "cover_letter": "Cover letter generation failed due to parsing error",
                "tone": "professional",
                "quality_score": 0.0,
                "word_count": 0
            }
    
    def _fallback_job_scoring(self, job_description: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback job scoring when AI is unavailable"""
        # Simple keyword matching fallback
        user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
        job_text = f"{job_description.get('title', '')} {job_description.get('description', '')}".lower()
        
        skill_matches = sum(1 for skill in user_skills if skill in job_text)
        total_skills = len(user_skills) if user_skills else 1
        
        relevance_score = min(skill_matches / total_skills, 1.0)
        
        return {
            "relevance_score": relevance_score,
            "skills_match": {"technical_skills": relevance_score, "soft_skills": 0.5},
            "experience_match": 0.5,
            "reasoning": "Fallback scoring based on keyword matching (AI unavailable)",
            "recommendations": ["Configure Gemini API for better analysis"]
        }
    
    def _fallback_cv_generation(self, user_profile: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """Fallback CV generation when AI is unavailable"""
        return {
            "tailored_cv": f"# CV for {user_profile.get('full_name', 'Candidate')}\n\nAI-powered CV generation unavailable. Please configure Gemini API.",
            "key_improvements": ["Configure AI service for CV generation"],
            "quality_score": 0.0,
            "recommendations": ["Set up Gemini API key in configuration"]
        }
    
    def _fallback_cover_letter_generation(self, user_profile: Dict[str, Any], job_description: str) -> Dict[str, Any]:
        """Fallback cover letter generation when AI is unavailable"""
        return {
            "cover_letter": "AI-powered cover letter generation unavailable. Please configure Gemini API.",
            "tone": "professional",
            "quality_score": 0.0,
            "word_count": 12
        }
    
    async def extract_job_search_parameters(self, user_message: str) -> Dict[str, Any]:
        """Extract job search parameters from natural language user message"""
        try:
            prompt = f"""
            Extract job search parameters from the following user message and return a JSON object with the parameters.
            
            User message: "{user_message}"
            
            Extract these parameters if mentioned:
            - keywords: Job title, skills, or technologies mentioned
            - location: Location, city, state, or "remote" if mentioned
            - salary_min: Minimum salary if mentioned (as integer)
            - salary_max: Maximum salary if mentioned (as integer)
            - experience_level: Entry, mid, senior, etc.
            - company_type: startup, tech, enterprise, etc.
            - job_type: full-time, part-time, contract, etc.
            
            Return only a valid JSON object with the extracted parameters.
            If a parameter is not mentioned, don't include it.
            
            Example:
            {{"keywords": "Python developer", "location": "San Francisco", "salary_min": 120000}}
            """
            
            if not self.model:
                logger.warning("Gemini not initialized, using fallback extraction")
                return self._fallback_parameter_extraction(user_message)
            
            response = await self.model.generate_content_async(prompt)
            
            if response and response.text:
                # Try to parse JSON from response
                response_text = response.text.strip()
                
                # Extract JSON from response (handle markdown formatting)
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                elif "{" in response_text and "}" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_text = response_text[json_start:json_end]
                else:
                    json_text = response_text
                
                try:
                    parameters = json.loads(json_text)
                    
                    # Normalize parameters - convert lists to strings
                    if isinstance(parameters, dict):
                        for key, value in parameters.items():
                            if isinstance(value, list):
                                parameters[key] = " ".join(str(v) for v in value)
                    
                    logger.info("Successfully extracted job search parameters", 
                              user_message=user_message, parameters=parameters)
                    return parameters
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from Gemini response", 
                                 response_text=response_text)
                    return self._fallback_parameter_extraction(user_message)
            else:
                logger.warning("Empty response from Gemini for parameter extraction")
                return self._fallback_parameter_extraction(user_message)
                
        except Exception as e:
            logger.error("Error extracting parameters with Gemini", error=str(e))
            return self._fallback_parameter_extraction(user_message)
    
    def _fallback_parameter_extraction(self, user_message: str) -> Dict[str, Any]:
        """Fallback parameter extraction using simple keyword matching"""
        import re
        
        parameters = {}
        message_lower = user_message.lower()
        
        # Extract keywords (common job titles and technologies)
        job_keywords = [
            "python", "java", "javascript", "react", "node.js", "nodejs", "angular", "vue",
            "developer", "engineer", "programmer", "analyst", "manager", "director",
            "software", "frontend", "backend", "fullstack", "full stack", "full-stack",
            "devops", "data scientist", "machine learning", "ml", "ai", "artificial intelligence",
            "qa", "quality assurance", "tester", "product manager", "scrum master",
            "designer", "ux", "ui", "architect", "lead", "senior", "junior", "intern"
        ]
        
        found_keywords = [kw for kw in job_keywords if kw in message_lower]
        if found_keywords:
            parameters["keywords"] = " ".join(found_keywords)
        
        # Extract location
        locations = [
            "san francisco", "sf", "new york", "nyc", "los angeles", "la", "chicago",
            "seattle", "austin", "boston", "denver", "atlanta", "miami", "dallas",
            "remote", "california", "texas", "florida", "washington"
        ]
        
        for location in locations:
            if location in message_lower:
                parameters["location"] = location
                break
        
        # Extract salary
        salary_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)'
        salary_matches = re.findall(salary_pattern, message_lower)
        
        if salary_matches:
            try:
                salary_str = salary_matches[0].replace(',', '').replace('k', '000')
                salary = int(salary_str)
                if salary > 1000:  # Reasonable salary threshold
                    parameters["salary_min"] = salary
            except ValueError:
                pass
        
        # Extract experience level
        if any(word in message_lower for word in ["senior", "sr", "lead"]):
            parameters["experience_level"] = "senior"
        elif any(word in message_lower for word in ["junior", "jr", "entry"]):
            parameters["experience_level"] = "entry"
        elif any(word in message_lower for word in ["mid", "intermediate"]):
            parameters["experience_level"] = "mid"
        
        return parameters


# Global AI service instance
ai_service = AIService()
