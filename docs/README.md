# Smart Assistant Documentation (Open WebUI Integrated)

This directory contains technical documentation for the Smart Assistant project as currently implemented: Open WebUI provides the primary UI and chat experience, while the Smart Assistant backend runs as a companion microservice for specialized features (job discovery, inbox management, intelligence briefing).

## Project Overview

- Primary platform: Open WebUI (chat, users, RAG, plugins/pipelines)
- Companion service: Smart Assistant FastAPI backend (microservice on HTTP)
- Data: SQLite by default via aiosqlite and Alembic migrations (optional Postgres/Redis)
- Integrations: LinkedIn scraping (Bright Data), Gemini, optional Airtable

See the detailed integration plan in the repository root: `INTEGRATION_PLAN.md`.

## Documentation Index

1. [System Architecture](./01-system-architecture.md) — Open WebUI + Smart Assistant topology and data flow
2. [Pipelines & Integration Framework](./02-agent-framework.md) — Open WebUI pipelines and microservice boundaries
3. [Data Architecture](./03-data-architecture.md) — Current schema, storage, and migrations
4. [API Design](./04-api-design.md) — Minimal REST endpoints and compatibility routes
5. [Job Pipeline](./05-job-pipeline.md) — LinkedIn scraping, dedup, relevance, Airtable (optional)
6. [Inbox Management](./06-inbox-management.md) — Email processing pipeline (status, scope)
7. [Intelligence Briefing](./07-intelligence-briefing.md) — Briefing generation pipeline (status, scope)
8. [Deployment Guide](./08-deployment-guide.md) — Running backend + Open WebUI (compose/tasks)
9. [Security Guide](./09-security-guide.md) — Current security posture and recommendations
10. [Testing Guide](./10-testing-guide.md) — Tests, how to run, and coverage focus

## High-Level Architecture (Current)

```
┌───────────────────────────────┐
│           Open WebUI          │
│  • Chat + Users + RAG         │
│  • Pipelines (Python plugins) │
│  • Admin/Settings             │
└───────────────┬───────────────┘
                │ HTTP (REST)
                ▼
┌───────────────────────────────┐
│   Smart Assistant Backend     │
│  • FastAPI microservice       │
│  • LinkedIn scraper (Node/BD) │
│  • Gemini analysis            │
│  • Airtable (optional)        │
└───────────────┬───────────────┘
                │ SQLAlchemy (async)
                ▼
┌───────────────────────────────┐
│        Database (default)     │
│  • SQLite + aiosqlite         │
│  • Alembic migrations         │
└───────────────────────────────┘
```

## Technology Stack (Current)

- UI: Open WebUI (SvelteKit app maintained upstream)
- Backend: FastAPI, SQLAlchemy (async), Pydantic
- DB: SQLite (default), optional Postgres; Alembic for migrations
- Caching/Vector DB: Optional (deferred unless enabled by Open WebUI config)
- AI: Google Gemini
- Extras: Airtable (optional), Bright Data Scraping Browser (LinkedIn)
- DevOps: Docker Compose; VS Code tasks; minimal CLI (`smartctl`)

## Getting Started

- Developer setup and run instructions are in the repo root `README.md` and `INTEGRATION_PLAN.md`.
- Use the VS Code tasks to start Backend and Open WebUI, or Docker Compose.

---

Document status: aligned to Open WebUI integration as of 2025-08-08.
