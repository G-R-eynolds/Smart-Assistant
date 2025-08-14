# Epic 2: Inbox Management

## Overview

An Open WebUI Pipeline calls the Smart Assistant inbox endpoint to categorize, summarize, and extract actions from recent emails. For demos without real credentials, the backend returns mock data.

## Flow

1) User asks “summarize my inbox” or similar → pipeline triggers
2) Pipeline POSTs to `/api/smart-assistant/inbox/process`
3) Backend runs the inbox pipeline (if configured) or returns realistic demo output
4) Pipeline formats a compact summary back into chat

## Endpoint contract

POST `/api/smart-assistant/inbox/process`

Request:
```json
{
    "credentials": { /* provider-specific auth, optional in demo */ },
    "filters": { /* date ranges, folders, labels, etc. */ }
}
```

Response (shape may vary when pipeline is enabled):
```json
{
    "status": "success",
    "data": {
        "unread_count": 12,
        "total_emails": 45,
        "important_emails": [ { "id": "...", "sender": "...", "subject": "...", "urgency": "high", "category": "job_opportunity", "received_at": "...", "preview": "..." } ],
        "categories": { "job_opportunity": 3, "work": 8, "personal": 2 },
        "action_items": [ { "description": "...", "priority": "high", "due_date": "2025-08-02" } ],
        "processing_time_ms": 1250
    }
}
```

## Notes

- Real inbox support requires provider OAuth and message fetchers; the current build focuses on pipeline wiring and presentation.
- Pipelines should keep summaries short and link to details when needed.

---

Next: [Epic 3: Intelligence Briefing](./07-intelligence-briefing.md).
            return ResponseAssessment(
                should_respond=True,
                confidence=0.7,
                reason="Important sender"
            )
        
        # Check for automated emails
        if self._is_automated_email(email):
            return ResponseAssessment(
                should_respond=False,
                confidence=0.9,
                reason="Automated email"
            )
        
        # Default assessment
        return ResponseAssessment(
            should_respond=False,
            confidence=0.6,
            reason="No clear response indicators"
        )
```

## User Experience Workflows

### Morning Briefing Workflow
```python
class MorningBriefingWorkflow:
    async def generate_morning_briefing(self, user_id: str) -> MorningBriefing:
        """Generate comprehensive morning email briefing"""
        
        # Get user's timezone and preferences
        user_prefs = await self.user_repo.get_user_preferences(user_id)
        timezone = user_prefs.get("timezone", "UTC")
        
        # Define time range (last 16 hours to cover evening emails)
        now = datetime.now(pytz.timezone(timezone))
        cutoff_time = now - timedelta(hours=16)
        
        # Fetch and process recent emails
        recent_emails = await self.email_repo.get_emails_since(user_id, cutoff_time)
        
        if not recent_emails:
            return MorningBriefing.empty(now.date())
        
        # Categorize and prioritize
        processed_emails = []
        for email in recent_emails:
            classification = await self.categorization_engine.categorize_email(
                email, {"user_id": user_id}
            )
            priority = await self.priority_scorer.calculate_priority_score(
                email, {"user_id": user_id}
            )
            
            email.classification = classification
            email.priority_score = priority
            processed_emails.append(email)
        
        # Generate briefing sections
        urgent_items = [e for e in processed_emails if e.priority_score.priority_level == "high"]
        action_required = await self._identify_action_required_emails(processed_emails, user_id)
        meetings_today = await self._extract_today_meetings(processed_emails, now.date())
        
        # Create summary sections
        summary_sections = {
            "urgent": await self._create_urgent_summary(urgent_items),
            "action_required": await self._create_action_summary(action_required),
            "meetings": await self._create_meeting_summary(meetings_today),
            "categories": await self._create_category_breakdown(processed_emails)
        }
        
        # Generate personalized greeting and insights
        greeting = await self._generate_personalized_greeting(user_id, now)
        insights = await self._generate_morning_insights(processed_emails, user_id)
        
        return MorningBriefing(
            date=now.date(),
            user_id=user_id,
            greeting=greeting,
            total_new_emails=len(recent_emails),
            urgent_count=len(urgent_items),
            action_required_count=len(action_required),
            summary_sections=summary_sections,
            key_insights=insights,
            generated_at=now
        )
```

## Performance Optimization

### Efficient Email Processing
```python
class EmailProcessingOptimizer:
    def __init__(self):
        self.batch_processor = BatchProcessor()
        self.cache_manager = CacheManager()
        self.model_selector = ModelSelector()
        
    async def optimize_email_processing(self, emails: List[Email], user_id: str):
        """Optimize email processing for cost and speed"""
        
        # Group emails by processing requirements
        grouped_emails = self._group_emails_by_complexity(emails)
        
        # Process each group with appropriate optimization
        for complexity_level, email_group in grouped_emails.items():
            if complexity_level == "simple":
                await self._process_simple_emails(email_group, user_id)
            elif complexity_level == "medium":
                await self._process_medium_emails(email_group, user_id)
            else:  # complex
                await self._process_complex_emails(email_group, user_id)
    
    def _group_emails_by_complexity(self, emails: List[Email]) -> Dict[str, List[Email]]:
        """Group emails by processing complexity for optimization"""
        
        groups = {"simple": [], "medium": [], "complex": []}
        
        for email in emails:
            complexity = self._assess_email_complexity(email)
            groups[complexity].append(email)
        
        return groups
    
    def _assess_email_complexity(self, email: Email) -> str:
        """Assess email processing complexity"""
        
        # Simple: Short, clear sender, no attachments
        if (len(email.plain_body) < 500 and 
            not email.attachments and 
            self._is_known_sender_pattern(email.sender)):
            return "simple"
        
        # Complex: Long content, attachments, unknown sender
        if (len(email.plain_body) > 2000 or 
            email.attachments or 
            self._requires_deep_analysis(email)):
            return "complex"
        
        # Medium: Everything else
        return "medium"
    
    async def _process_simple_emails(self, emails: List[Email], user_id: str):
        """Fast processing for simple emails"""
        
        # Use basic classification rules
        # Batch API calls for efficiency
        # Cache common patterns
        
        batch_size = 50
        for batch in self._create_batches(emails, batch_size):
            await self._process_simple_batch(batch, user_id)
    
    async def _process_complex_emails(self, emails: List[Email], user_id: str):
        """Detailed processing for complex emails"""
        
        # Individual processing with full AI analysis
        # Use higher-capability models
        # Generate detailed insights
        
        for email in emails:
            await self._process_complex_individual(email, user_id)
```

---

**Next**: Review [Epic 3: Intelligence Briefing](./07-intelligence-briefing.md) for personalized news curation and synthesis workflows.
