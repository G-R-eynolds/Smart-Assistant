# Epic 1: Job Opportunity Pipeline

## Overview

This pipeline turns a chat request like “find remote senior Python jobs” into actionable results by calling the Smart Assistant backend from an Open WebUI Pipeline. The backend performs AI keyword extraction, scrapes LinkedIn, deduplicates by URL, and (optionally) analyzes and saves top jobs.

## Flow (High level)

1) Pipeline trigger in Open WebUI detects a job-search intent.
2) Pipeline POSTs to `/api/smart-assistant/jobs/search` with the query and options.
3) Backend:
    - Uses Gemini to extract structured search terms (keywords, location, level, type)
    - Scrapes LinkedIn via `LinkedInScraperV2`
    - Deduplicates with `job_deduplication_service`
    - Optionally analyzes relevance and generates cover letters in the background
    - Optionally saves high-relevance jobs to Airtable
4) Pipeline renders immediate results in chat; background actions continue server-side.

## Endpoint contract

POST `/api/smart-assistant/jobs/search`

Request (selected fields):
- `query` or `keywords`: string (required)
- `location`: string (optional)
- `experience_level`: string (optional)
- `job_type`: string (optional)
- `date_posted`: string, default "week"
- `limit`: number, default 25
- `generate_cover_letters`: boolean, default true
- `save_to_airtable`: boolean, default true
- `min_relevance_score`: number, default 0.7

Response (selected fields):
- `status`: "success" | "error"
- `count`: number
- `message`: string
- `jobs`: array of job objects (title, company, location, job_url, description, etc.)
- `ai_extraction`: object (original_query, extracted_keywords, location, level, type, reasoning)

Notes:
- Immediate response returns scraped jobs; deeper AI analysis and Airtable writes run as a background task.
- Deduplication prevents reprocessing the same job URLs across runs.

## Components

- AI keyword extraction: `app/core/gemini_client.py`
- LinkedIn scraping: `app/core/linkedin_scraper_v2.py`
- Deduplication: `app/core/job_deduplication.py`
- Airtable (optional): `app/core/airtable_client.py`

## CV helpers

Utility endpoints used by other features and pipelines:
- GET `/api/smart-assistant/cv/info`
- GET `/api/smart-assistant/cv/summary`
- POST `/api/smart-assistant/cv/refresh`

## Future extensions (non-blocking)

- Additional sources beyond LinkedIn
- User-tunable scoring thresholds via pipeline valves
- Persisted job/application tracking (Postgres profile)

---

Next: [Epic 2: Inbox Management](./06-inbox-management.md).
