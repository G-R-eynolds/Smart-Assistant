# System Architecture (Current)

## Overview

The Smart Assistant now runs as a companion FastAPI microservice alongside Open WebUI, which serves as the primary UI, user/accounts system, and plugin/pipeline host. Smart Assistant exposes focused REST endpoints (job discovery, inbox processing, intelligence briefing) that Open WebUI pipelines call. SQLite is the default database for development; Alembic manages schema migrations.

## Architectural Principles

1) Separation of concerns: Open WebUI handles UI/auth/RAG; Smart Assistant provides specialized features via APIs.
2) Simplicity first: Default to SQLite + aiosqlite for local dev; opt-in to Postgres/Redis when needed.
3) Compatibility: Maintain Open WebUI–compatible routes where helpful; use pipelines for integration.
4) Observability: Health endpoints, simple logs, and minimal test coverage for core flows.

## High-Level Topology

```
Client (Browser)
        │
        ▼
Open WebUI (primary)
    • Chat and pipelines
    • RAG/documents
    • Admin/Users
        │  HTTP
        ▼
Smart Assistant Backend (FastAPI)
    • LinkedIn scraper (via Bright Data, Node helper)
    • Job dedup + relevance scoring (Gemini)
    • Inbox/Briefing processors
        │  SQLAlchemy (async)
        ▼
SQLite (default) / Postgres (optional)
```

## Core Components

### Open WebUI
- Provides chat interface, user management, and the pipelines framework.
- Hosts Python pipeline plugins that trigger Smart Assistant endpoints.

### Smart Assistant Backend (FastAPI)
- Exposes REST endpoints under `/api/smart-assistant/...` for:
    - Job search/scraping and analysis
    - Inbox processing (when configured)
    - Intelligence briefing generation
- Integrates with Google Gemini; optionally Airtable.
- Offers a minimal CLI (`smartctl`) for health checks and test searches.

### Data Layer
- Default: SQLite with `aiosqlite` driver; schema managed via Alembic.
- Optional: Postgres/Redis enabled via Docker Compose profiles.

## Communication

- Open WebUI Pipelines → Smart Assistant REST (JSON over HTTP)
- Backend → SQLite/Postgres via SQLAlchemy (async engine/sessions)

## Non-Goals (for now)

- CrewAI-style multi-agent orchestration inside the backend.
- Mandatory vector DB/Qdrant. Open WebUI can provide RAG when needed.

## Deployment Notes

- Local dev uses VS Code tasks or Docker Compose to run both services.
- Health endpoint: `GET /health` (backend).

---

Next: [Pipelines & Integration](./02-agent-framework.md)
