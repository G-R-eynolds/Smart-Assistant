"""
Smart Assistant Inbox Management Pipeline Function for Open WebUI

Implements Phase 1.2 of the integration plan: Inbox Management Pipeline Function
Integrates Smart Assistant's email processing capabilities into Open WebUI's pipeline system.

This function:
- Detects email-related commands in chat messages
- Communicates with Smart Assistant email processing service
- Formats and displays email summaries, priorities, and action items
- Provides email management functionality through chat interface
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
    Smart Assistant Inbox Management Pipeline Function
    
    This pipeline function provides email processing capabilities through
    Open WebUI's chat interface, enabling users to check emails, process
    their inbox, and get email summaries via chat commands.
    """
    
    # Required pipeline attributes
    id = "smart_assistant_inbox_management"
    name = "Smart Assistant Inbox Management"
    valves = None  # Will be initialized in __init__
    
    class Valves(BaseModel):
        """Configuration valves for the inbox management pipeline"""
        smart_assistant_url: str = "http://localhost:8001"
        enabled: bool = True
        timeout_seconds: int = 20
        max_emails_display: int = 10
        privacy_mode: bool = True
        log_level: str = "INFO"
        LOG_LEVEL: str = "INFO"
    
    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves()
        USE_GEMINI_PROCESSING: bool = True
        GEMINI_API_KEY: str = ""
        LOG_LEVEL: str = "INFO"
        PRIVACY_MODE: bool = True  # Anonymize sensitive email content
    
    def __init__(self):
        self.type = "filter"
        self.name = "Smart Assistant Inbox Management"
        self.id = "smart_assistant_inbox"
        self.description = "AI-powered email processing and inbox management pipeline"
        
        # Email-related trigger phrases
        self.email_triggers = [
            "check email", "process inbox", "email summary", "unread emails",
            "inbox status", "email overview", "new emails", "important emails",
            "email updates", "mail summary", "gmail check", "email digest"
        ]
        
        # Initialize valves
        self.valves = self.Valves()
        
        # Set up logging
        logging.basicConfig(level=getattr(logging, self.valves.LOG_LEVEL))
    
    async def inlet(self, body: Dict[str, Any], user: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process incoming chat messages for email-related commands
        
        Args:
            body: Chat request body containing messages
            user: User information dict
            
        Returns:
            Modified body with email summary injected (if applicable)
        """
        try:
            if not self.valves.enabled:
                return body
            
            # Extract the last user message
            messages = body.get("messages", [])
            if not messages:
                return body
            
            last_message = messages[-1]
            
            # Skip if not a dictionary or not a user message
            if not isinstance(last_message, dict) or last_message.get("role") != "user":
                return body
                
            message_content = last_message.get("content", "")
            
            # Skip system-generated messages
            if (message_content.startswith("### Task:") or 
                message_content.startswith("### Follow-up") or
                "suggest" in message_content.lower() and "follow-up" in message_content.lower()):
                return body
            
            # Check if this contains email-related triggers
            if not self._contains_email_trigger(message_content):
                return body
            message_content = last_message.get("content", "").lower()
            
            # Check if message contains email-related triggers
            if not self._contains_email_trigger(message_content):
                return body
            
            logger.info(
                "Inbox management triggered",
                user_id=user.get("id") if user else None,
                message_preview=message_content[:100]
            )
            
            # Extract email processing parameters
            processing_params = self._extract_email_parameters(message_content)
            
            # Call Smart Assistant inbox processing service
            inbox_result = await self._process_inbox(processing_params, user)
            
            if inbox_result:
                # Format and inject email summary into conversation
                formatted_response = await self._format_inbox_response(inbox_result)
                
                # Enhance the original message with inbox summary
                enhanced_content = f"{last_message['content']}\\n\\n{formatted_response}"
                body["messages"][-1]["content"] = enhanced_content
                
                logger.info(
                    "Inbox processing completed",
                    unread_count=inbox_result.get("unread_count", 0),
                    user_id=user.get("id") if user else None
                )
            else:
                # Add a message indicating inbox couldn't be processed
                error_message = "\\n\\n📧 **Inbox Status**: Unable to access inbox at this time. Please check your email connection settings."
                body["messages"][-1]["content"] += error_message
            
            return body
            
        except Exception as e:
            logger.error(f"Inbox management pipeline error: {e}")
            # Add error message to chat but don't break the flow
            error_message = "\\n\\n❌ **Email Error**: Unable to process inbox at this time. Please try again later."
            if "messages" in body and body["messages"]:
                body["messages"][-1]["content"] += error_message
            return body
    
    def _contains_email_trigger(self, message: str) -> bool:
        """Check if message contains email-related trigger phrases"""
        message_lower = message.lower()
        return any(trigger in message_lower for trigger in self.email_triggers)
    
    def _extract_email_parameters(self, message: str) -> Dict[str, Any]:
        """Extract email processing parameters from message"""
        params = {}
        message_lower = message.lower()
        
        # Determine processing type
        if any(term in message_lower for term in ["unread", "new"]):
            params["filter"] = "unread"
        elif any(term in message_lower for term in ["important", "priority", "urgent"]):
            params["filter"] = "important"
        elif any(term in message_lower for term in ["today", "recent"]):
            params["filter"] = "recent"
        else:
            params["filter"] = "all"
        
        # Extract requested actions
        if any(term in message_lower for term in ["summary", "digest", "overview"]):
            params["include_summary"] = True
        if any(term in message_lower for term in ["action", "response", "reply"]):
            params["include_actions"] = True
        
        return params
    
    async def _process_inbox(
        self, 
        processing_params: Dict[str, Any], 
        user: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call Smart Assistant inbox processing service
        
        Makes HTTP request to Smart Assistant backend to process inbox
        with the specified parameters.
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.valves.TIMEOUT_SECONDS)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Prepare request payload
                payload = {
                    "filter": processing_params.get("filter", "unread"),
                    "include_summary": processing_params.get("include_summary", True),
                    "include_actions": processing_params.get("include_actions", True),
                    "max_emails": self.valves.MAX_EMAILS_DISPLAY,
                    "privacy_mode": self.valves.PRIVACY_MODE
                }
                
                # Add authentication if user token available
                headers = {"Content-Type": "application/json"}
                if user and user.get("token"):
                    headers["Authorization"] = f"Bearer {user['token']}"
                
                url = f"{self.valves.SMART_ASSISTANT_URL}/api/v1/inbox/process"
                
                async with session.post(
                    url,
                    json=payload,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Inbox processing successful: {result.get('emails_processed', 0)} emails processed")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Smart Assistant Inbox API error {response.status}: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Inbox processing request timed out")
            return None
        except Exception as e:
            logger.error(f"Inbox processing request failed: {e}")
            return None
    
    async def _format_inbox_response(self, inbox_result: Dict[str, Any]) -> str:
        """
        Format inbox processing results for chat display
        
        Creates a comprehensive inbox summary with email priorities,
        action items, and suggested responses.
        """
        unread_count = inbox_result.get("unread_count", 0)
        total_emails = inbox_result.get("total_emails", 0)
        important_emails = inbox_result.get("important_emails", [])
        categories = inbox_result.get("categories", {})
        action_items = inbox_result.get("action_items", [])
        
        # Build formatted response
        response_parts = []
        response_parts.append("\\n\\n📧 **Inbox Summary**")
        
        # Overall stats
        if unread_count > 0:
            response_parts.append(f"📬 **{unread_count} unread** out of {total_emails} total emails")
        else:
            response_parts.append("✅ **Inbox up to date** - No unread emails")
        
        # Email categories
        if categories:
            response_parts.append("\\n📊 **Email Categories:**")
            for category, count in categories.items():
                if count > 0:
                    emoji = self._get_category_emoji(category)
                    response_parts.append(f"  {emoji} {category.title()}: {count}")
        
        # Important emails highlight
        if important_emails:
            response_parts.append("\\n🔥 **Priority Emails:**")
            for i, email in enumerate(important_emails[:3], 1):  # Show top 3
                sender = email.get("sender", "Unknown Sender")
                subject = email.get("subject", "No Subject")
                urgency = email.get("urgency", "medium")
                
                # Truncate subject for display
                display_subject = subject[:50] + "..." if len(subject) > 50 else subject
                urgency_emoji = "🔴" if urgency == "high" else "🟡" if urgency == "medium" else "🟢"
                
                response_parts.append(f"  {i}. {urgency_emoji} **{sender}**: {display_subject}")
        
        # Action items
        if action_items:
            response_parts.append("\\n⚡ **Suggested Actions:**")
            for i, action in enumerate(action_items[:5], 1):  # Show top 5 actions
                action_text = action.get("description", "")
                priority = action.get("priority", "medium")
                priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                
                response_parts.append(f"  {i}. {priority_emoji} {action_text}")
        
        # Quick stats summary
        if unread_count > 0:
            response_parts.append("\\n💡 **Quick Actions**: Say 'reply to email [number]' or 'mark as read' to manage emails.")
        
        return "\\n".join(response_parts)
    
    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for email category"""
        emoji_map = {
            "work": "💼",
            "personal": "👤", 
            "promotional": "🛍️",
            "social": "👥",
            "finance": "💰",
            "travel": "✈️",
            "health": "🏥",
            "education": "🎓",
            "shopping": "🛒",
            "bills": "📄",
            "newsletters": "📰",
            "notifications": "🔔"
        }
        return emoji_map.get(category.lower(), "📧")


# Required for Open WebUI to recognize this as a pipeline function
def __init__():
    return Pipeline()
    async def process_inbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a direct inbox management request from the API
        
        This method is called by the API endpoint to process inbox requests
        without going through the pipeline inlet/outlet system.
        
        Args:
            params: Dictionary with request parameters
                - user_id: ID of the requesting user
                - credentials: Email account credentials (OAuth token, etc.)
                - filters: Email filtering options
        
        Returns:
            Dictionary with inbox processing results
                - unread_count: Number of unread emails
                - total_emails: Total number of emails in inbox
                - important_emails: List of important emails
                - action_items: List of extracted action items
                - processing_time_ms: Processing time in milliseconds
        """
        try:
            # Extract user info
            user_id = params.get("user_id")
            
            logger.info(
                "Processing direct inbox request",
                user_id=user_id
            )
            
            # In a real implementation, we'd communicate with the email service
            # For now, return mock data
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
                    "action_items": [
                        {
                            "description": "Respond to recruiter about software engineer position",
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
                    "action_items": [],
                    "processing_time_ms": 0
                }
            }
