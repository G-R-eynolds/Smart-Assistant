"""
Smart Assistant Intelligence Briefing Pipeline Function for Open WebUI

Implements Phase 1.3 of the integration plan: Intelligence Briefing Pipeline Function
Integrates Smart Assistant's intelligence briefing capabilities into Open WebUI's pipeline system.

This function:
- Detects briefing-related commands in chat messages
- Generates personalized daily intelligence briefings
- Includes market news, technology trends, and career insights
- Provides actionable recommendations and insights
"""

import asyncio
import json
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date

import aiohttp
import structlog
from pydantic import BaseModel

# Set up logging
logger = structlog.get_logger()


class Pipeline:
    """
    Smart Assistant Intelligence Briefing Pipeline Function
    
    This pipeline function generates personalized intelligence briefings
    through Open WebUI's chat interface, providing users with market updates,
    tech trends, and career insights via chat commands.
    """
    
    # Required pipeline attributes
    id = "smart_assistant_intelligence_briefing"
    name = "Smart Assistant Intelligence Briefing"
    valves = None  # Will be initialized in __init__
    
    class Valves(BaseModel):
        """Configuration valves for the intelligence briefing pipeline"""
        smart_assistant_url: str = "http://localhost:8001"
        enabled: bool = True
        timeout_seconds: int = 45
        use_gemini_analysis: bool = True
        cache_duration_hours: int = 6
        max_briefing_items: int = 15
        log_level: str = "INFO"
    
    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves()
        GEMINI_API_KEY: str = ""
        CACHE_DURATION_HOURS: int = 6
        MAX_NEWS_ITEMS: int = 15
        INCLUDE_MARKET_DATA: bool = True
        INCLUDE_TECH_TRENDS: bool = True
        INCLUDE_CAREER_INSIGHTS: bool = True
        LOG_LEVEL: str = "INFO"
    
    def __init__(self):
        self.type = "filter"
        self.name = "Smart Assistant Intelligence Briefing"
        self.id = "smart_assistant_briefing"
        self.description = "AI-powered intelligence briefing and market analysis pipeline"
        
        # Briefing-related trigger phrases
        self.briefing_triggers = [
            "daily briefing", "intelligence update", "news summary", "generate briefing",
            "market update", "tech trends", "industry news", "career insights",
            "what's happening", "latest news", "market analysis", "intelligence report",
            "briefing", "daily digest", "news digest", "today's news"
        ]
        
        # Initialize valves
        self.valves = self.Valves()
        
        # Set up logging
        logging.basicConfig(level=getattr(logging, self.valves.LOG_LEVEL))
    
    async def inlet(self, body: Dict[str, Any], user: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process incoming chat messages for briefing-related commands
        
        Args:
            body: Chat request body containing messages
            user: User information dict
            
        Returns:
            Modified body with intelligence briefing injected (if applicable)
        """
        try:
            if not self.valves.ENABLED:
                return body
            
            # Extract the last user message
            messages = body.get("messages", [])
            if not messages:
                return body
            
            last_message = messages[-1]
            message_content = last_message.get("content", "").lower()
            
            # Check if message contains briefing-related triggers
            if not self._contains_briefing_trigger(message_content):
                return body
            
            logger.info(
                "Intelligence briefing triggered",
                user_id=user.get("id") if user else None,
                message_preview=message_content[:100]
            )
            
            # Extract briefing parameters
            briefing_params = self._extract_briefing_parameters(message_content)
            
            # Generate intelligence briefing
            briefing_result = await self._generate_briefing(briefing_params, user)
            
            if briefing_result:
                # Format and inject briefing into conversation
                formatted_response = await self._format_briefing_response(briefing_result)
                
                # Enhance the original message with intelligence briefing
                enhanced_content = f"{last_message['content']}\\n\\n{formatted_response}"
                body["messages"][-1]["content"] = enhanced_content
                
                logger.info(
                    "Intelligence briefing completed",
                    items_count=len(briefing_result.get("news_items", [])),
                    user_id=user.get("id") if user else None
                )
            else:
                # Add a message indicating briefing couldn't be generated
                error_message = "\\n\\n📊 **Intelligence Briefing**: Unable to generate briefing at this time. Please try again later."
                body["messages"][-1]["content"] += error_message
            
            return body
            
        except Exception as e:
            logger.error(f"Intelligence briefing pipeline error: {e}")
            # Add error message to chat but don't break the flow
            error_message = "\\n\\n❌ **Briefing Error**: Unable to generate intelligence briefing at this time. Please try again later."
            if "messages" in body and body["messages"]:
                body["messages"][-1]["content"] += error_message
            return body
    
    def _contains_briefing_trigger(self, message: str) -> bool:
        """Check if message contains briefing-related trigger phrases"""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.briefing_triggers)
    
    def _extract_briefing_parameters(self, message: str) -> Dict[str, Any]:
        """Extract briefing generation parameters from message"""
        params = {}
        message_lower = message.lower()
        
        # Determine briefing focus
        if any(term in message_lower for term in ["market", "financial", "economy"]):
            params["focus"] = "market"
        elif any(term in message_lower for term in ["tech", "technology", "ai", "software"]):
            params["focus"] = "technology"
        elif any(term in message_lower for term in ["career", "job", "industry"]):
            params["focus"] = "career"
        else:
            params["focus"] = "general"
        
        # Determine scope
        if any(term in message_lower for term in ["today", "daily"]):
            params["timeframe"] = "daily"
        elif any(term in message_lower for term in ["week", "weekly"]):
            params["timeframe"] = "weekly"
        else:
            params["timeframe"] = "daily"
        
        # Determine depth
        if any(term in message_lower for term in ["detailed", "deep", "comprehensive"]):
            params["depth"] = "detailed"
        elif any(term in message_lower for term in ["brief", "quick", "summary"]):
            params["depth"] = "brief"
        else:
            params["depth"] = "standard"
        
        return params
    
    async def _generate_briefing(
        self, 
        briefing_params: Dict[str, Any], 
        user: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call Smart Assistant intelligence briefing service
        
        Makes HTTP request to Smart Assistant backend to generate
        personalized intelligence briefing.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.valves.TIMEOUT_SECONDS)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Prepare request payload
                payload = {
                    "focus": briefing_params.get("focus", "general"),
                    "timeframe": briefing_params.get("timeframe", "daily"),
                    "depth": briefing_params.get("depth", "standard"),
                    "include_market_data": self.valves.INCLUDE_MARKET_DATA,
                    "include_tech_trends": self.valves.INCLUDE_TECH_TRENDS,
                    "include_career_insights": self.valves.INCLUDE_CAREER_INSIGHTS,
                    "max_items": self.valves.MAX_NEWS_ITEMS,
                    "use_cache": True,
                    "cache_duration_hours": self.valves.CACHE_DURATION_HOURS
                }
                
                # Add authentication if user token available
                headers = {"Content-Type": "application/json"}
                if user and user.get("token"):
                    headers["Authorization"] = f"Bearer {user['token']}"
                
                url = f"{self.valves.SMART_ASSISTANT_URL}/api/v1/intelligence/briefing"
                
                async with session.post(
                    url,
                    json=payload,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Intelligence briefing generated: {len(result.get('news_items', []))} items")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Smart Assistant Intelligence API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Intelligence briefing request timed out")
            return None
        except Exception as e:
            logger.error(f"Intelligence briefing request failed: {e}")
            return None
    
    async def _format_briefing_response(self, briefing_result: Dict[str, Any]) -> str:
        """
        Format intelligence briefing results for chat display
        
        Creates a comprehensive briefing with market data, tech trends,
        and personalized career insights.
        """
        generated_at = briefing_result.get("generated_at", datetime.now().isoformat())
        news_items = briefing_result.get("news_items", [])
        market_data = briefing_result.get("market_data", {})
        tech_trends = briefing_result.get("tech_trends", [])
        career_insights = briefing_result.get("career_insights", [])
        key_takeaways = briefing_result.get("key_takeaways", [])
        
        # Build formatted response
        response_parts = []
        response_parts.append("\\n\\n📊 **Intelligence Briefing**")
        response_parts.append(f"*Generated: {self._format_timestamp(generated_at)}*\\n")
        
        # Executive summary
        if key_takeaways:
            response_parts.append("🎯 **Key Takeaways:**")
            for takeaway in key_takeaways[:3]:
                response_parts.append(f"• {takeaway}")
            response_parts.append("")
        
        # Market data section
        if market_data and self.valves.INCLUDE_MARKET_DATA:
            response_parts.append("📈 **Market Overview:**")
            
            if market_data.get("major_indices"):
                indices = market_data["major_indices"]
                for index, data in indices.items():
                    change = data.get("change", 0)
                    change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    response_parts.append(f"  {change_emoji} {index}: {data.get('value', 'N/A')} ({change:+.2f}%)")
            
            if market_data.get("crypto_overview"):
                crypto = market_data["crypto_overview"]
                response_parts.append(f"  ₿ Bitcoin: ${crypto.get('btc_price', 'N/A')} ({crypto.get('btc_change', 0):+.1f}%)")
            
            response_parts.append("")
        
        # Technology trends
        if tech_trends and self.valves.INCLUDE_TECH_TRENDS:
            response_parts.append("🚀 **Technology Trends:**")
            for i, trend in enumerate(tech_trends[:4], 1):
                title = trend.get("title", "Unknown Trend")
                impact = trend.get("impact_score", 0)
                impact_emoji = "🔥" if impact > 8 else "⚡" if impact > 6 else "💡"
                
                response_parts.append(f"  {i}. {impact_emoji} {title}")
                if trend.get("summary"):
                    response_parts.append(f"     {trend['summary'][:80]}...")
            response_parts.append("")
        
        # Career insights
        if career_insights and self.valves.INCLUDE_CAREER_INSIGHTS:
            response_parts.append("💼 **Career Insights:**")
            for i, insight in enumerate(career_insights[:3], 1):
                title = insight.get("title", "Career Update")
                relevance = insight.get("relevance", "medium")
                relevance_emoji = "🔴" if relevance == "high" else "🟡" if relevance == "medium" else "🟢"
                
                response_parts.append(f"  {i}. {relevance_emoji} {title}")
                if insight.get("description"):
                    response_parts.append(f"     {insight['description'][:80]}...")
            response_parts.append("")
        
        # Top news items
        if news_items:
            response_parts.append("📰 **Top News:**")
            for i, item in enumerate(news_items[:5], 1):
                title = item.get("title", "News Item")
                source = item.get("source", "Unknown Source")
                category = item.get("category", "general")
                category_emoji = self._get_news_category_emoji(category)
                
                # Truncate title for display
                display_title = title[:60] + "..." if len(title) > 60 else title
                response_parts.append(f"  {i}. {category_emoji} **{display_title}**")
                response_parts.append(f"     *Source: {source}*")
        
        # Action items
        response_parts.append("\\n💡 **Recommended Actions:**")
        response_parts.append("• Review job market trends for new opportunities")
        response_parts.append("• Stay updated on emerging technologies in your field")
        response_parts.append("• Consider skill development based on industry trends")
        
        return "\\n".join(response_parts)
    
    def _format_timestamp(self, timestamp_str: str) -> str:
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            return "Today"
    
    def _get_news_category_emoji(self, category: str) -> str:
        """Get emoji for news category"""
        emoji_map = {
            "technology": "💻",
            "business": "💼",
            "finance": "💰",
            "market": "📈",
            "ai": "🤖",
            "startup": "🚀",
            "career": "👔",
            "education": "🎓",
            "health": "🏥",
            "science": "🔬",
            "politics": "🏛️",
            "world": "🌍",
            "sports": "⚽",
            "entertainment": "🎬"
        }
        return emoji_map.get(category.lower(), "📰")


# Required for Open WebUI to recognize this as a pipeline function
def __init__():
    return Pipeline()
    async def generate_briefing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an intelligence briefing directly from the API
        
        This method is called by the API endpoint to generate briefings
        without going through the pipeline inlet/outlet system.
        
        Args:
            params: Dictionary with request parameters
                - user_id: ID of the requesting user
                - preferences: User preferences for briefing content
        
        Returns:
            Dictionary with intelligence briefing
                - generated_at: Timestamp of generation
                - news_items: List of relevant news articles
                - market_updates: List of market updates
                - career_insights: Career-related insights
                - key_takeaways: Summary of key points
        """
        try:
            # Extract user info
            user_id = params.get("user_id")
            preferences = params.get("preferences", {})
            
            logger.info(
                "Generating intelligence briefing",
                user_id=user_id
            )
            
            # In a real implementation, we'd pull data from sources and generate insights
            # For now, return mock data
            return {
                "status": "success",
                "data": {
                    "generated_at": datetime.now().isoformat(),
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
                            "url": "https://example.com/remote-work-2025"
                        }
                    ],
                    "market_updates": [
                        {
                            "title": "Tech Sector Growth",
                            "category": "industry",
                            "summary": "Tech sector showing 12% YoY growth despite economic challenges",
                            "trend": "positive"
                        },
                        {
                            "title": "Developer Hiring Trends",
                            "category": "employment",
                            "summary": "Increased demand for ML/AI specialists and full-stack developers",
                            "trend": "positive"
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
            logger.error(f"Briefing generation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": {
                    "generated_at": datetime.now().isoformat(),
                    "news_items": [],
                    "market_updates": [],
                    "career_insights": [],
                    "key_takeaways": [],
                    "generation_time_ms": 0
                }
            }
