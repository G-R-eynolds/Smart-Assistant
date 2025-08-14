# API Design Specification

## Overview

The Smart Assistant exposes a simple REST API used primarily by Open WebUI Pipelines. There is no GraphQL or WebSocket layer. Endpoints are versioned by path segments and grouped under `/api/smart-assistant` for feature routes, with a few compatibility endpoints for Open WebUI under `/api` and `/api/v1`.

## Core Principles

1. REST-first: Standard HTTP verbs, status codes, and JSON bodies.
2. Minimal surface: Only endpoints needed by pipelines and basic admin flows.
3. Async by default: FastAPI with async handlers for I/O-bound work.
4. Clear versioning: Namespace feature endpoints under `/api/smart-assistant`.
5. Pragmatic security: Bearer auth placeholder today; tighten in production.

## Authentication & CORS

- Auth: Bearer token in `Authorization: Bearer <token>`. The demo build accepts a mock token and returns a demo user. Replace with real JWT verification in production.
- CORS: Wide-open in development (`allow_origins=["*"]`). Restrict to your Open WebUI origin in production.

## Open WebUI Compatibility Endpoints

- GET `/api/health` → `{ status: true }`
- GET `/api/config` → Open WebUI boot config
- GET `/api/models` → List of pseudo models (used to surface pipelines)
- Auth stubs under `/api/v1/auths/*` for local login/signup during demos

These exist to make Open WebUI happy; they are not the primary integration points.

## Smart Assistant Endpoints

Base path: `/api/smart-assistant`

1) GET `/health`
- Purpose: Liveness for the Smart Assistant feature set
- Response: `{ status: "healthy", timestamp: <iso>, components: { job_discovery: bool, inbox_management: bool, intelligence_briefing: bool } }`

2) POST `/jobs/search`
- Purpose: Run the job search flow (AI keyword extraction → LinkedIn scrape → optional background AI analysis + Airtable save)
- Request JSON (selected fields):
	- `query` or `keywords` (string, required)
	- `location` (string, optional)
	- `experience_level` (string, optional)
	- `job_type` (string, optional)
	- `date_posted` (string, default "week")
	- `limit` (int, default 25)
	- `generate_cover_letters` (bool, default true)
	- `save_to_airtable` (bool, default true)
	- `min_relevance_score` (float, default 0.7)
- Response JSON (selected fields):
	- `status` ("success")
	- `count` (int)
	- `message` (string)
	- `jobs` (array of job objects)
	- `ai_extraction` (object with extracted parameters and reasoning)

3) POST `/inbox/process`
- Purpose: Process inbox (categorize/summarize). Uses pipeline when configured; falls back to mock data for demos.
- Request JSON: `{ credentials: {...}, filters: {...} }`
- Response JSON: `{ status: "success", data: { unread_count, total_emails, important_emails, categories, action_items, processing_time_ms } }`

4) POST `/briefing/generate`
- Purpose: Generate an intelligence briefing using the pipeline (falls back to demo data)
- Request JSON: `{ preferences: {...} }`
- Response JSON: `{ status, data: { generated_at, news_items, market_data, tech_trends, career_insights, key_takeaways, generation_time_ms } }`

5) POST `/job-discovery/run`
- Purpose: Legacy/dev helper to run the discovery pipeline directly
- Request JSON: `{ query: "..." }`
- Response JSON: `{ status, message, jobs }`

6) CV Utilities
- GET `/cv/info` → status of current CV file
- GET `/cv/summary` → summary of cached CV text
- POST `/cv/refresh` → refresh the CV text cache

## Errors

- Validation: 400 with `{ "detail": "..." }` when required fields are missing
- Server errors: 500 with `{ "detail": "..." }` (FastAPI default) or `{ status: "error", message|error: "..." }` in some handlers
- Pipelines should surface a concise error message to the user

## OpenAPI Docs

Interactive API docs are available at `/docs` (Swagger UI) and `/openapi.json`.

---

Next: Review [Epic 1: Job Opportunity Pipeline](./05-job-pipeline.md) for the end-to-end search and processing flow.
