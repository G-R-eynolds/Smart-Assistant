# Epic 3: Intelligence Briefing

## Overview

An Open WebUI Pipeline asks the backend to generate a concise daily briefing. The backend runs a pipeline when available, or returns demo data for local testing.

## Flow

1) User asks “give me a briefing for today” → pipeline triggers
2) Pipeline POSTs to `/api/smart-assistant/briefing/generate`
3) Backend generates sections: news_items, market_data, tech_trends, career_insights, and key_takeaways
4) Pipeline formats a short, scannable summary in chat with links

## Endpoint contract

POST `/api/smart-assistant/briefing/generate`

Request:
```json
{
    "preferences": { "interests": ["ai"], "time_range": "24h" }
}
```

Response (selected fields):
```json
{
    "status": "success",
    "data": {
        "generated_at": "2025-08-01T10:45:00Z",
        "news_items": [ { "title": "...", "source": "...", "category": "...", "summary": "...", "published_at": "...", "relevance": "high", "url": "..." } ],
        "market_data": { "job_market_health": "strong" },
        "tech_trends": [ { "title": "...", "impact_score": 8.7, "summary": "..." } ],
        "career_insights": [ { "title": "...", "relevance": "immediate", "description": "..." } ],
        "key_takeaways": [ "..." ],
        "generation_time_ms": 2100
    }
}
```

## Notes

- Keep the chat output brief, with optional “expand” toggles in the UI.
- When preferences are omitted, use reasonable defaults server-side.

---

Next: [Implementation Guide: Deployment Strategy](./08-deployment-guide.md).
