# Pipelines & Integration Framework (Open WebUI)

## Overview

Open WebUI Pipelines invoke the Smart Assistant REST API to perform specialized tasks (job discovery, inbox processing, intelligence briefings). Pipelines are lightweight Python modules loaded by Open WebUI that can inspect/modify chat messages and call external services (our backend). This replaces the earlier internal “multi-agent” approach.

## Core Principles

1) Single responsibility: Each pipeline focuses on one capability (jobs, inbox, briefing).
2) Minimal coupling: Pipelines call the backend via HTTP with small, versionable JSON contracts.
3) Human-in-the-loop: Results surface in chat; follow-ups are user-triggered.
4) Cost-aware: Prefer lightweight checks; rely on backend caching/dedup where possible.

## Pipelines (current)

- Job Discovery: Matches triggers like “find jobs …”; POSTs to `/api/smart-assistant/jobs/search`; renders a compact list with links and relevance.
- Inbox Management: Optional; POSTs to `/api/smart-assistant/inbox/process`; returns categorized summary and top actions.
- Intelligence Briefing: POSTs to `/api/smart-assistant/briefing/generate`; returns a short briefing with sections.

## Pipeline contract (minimal)

Each pipeline provides:
- `id`, `name` strings
- `Valves` Pydantic model for config (e.g., `smart_assistant_url`, `api_key`, `timeout_seconds`, limits)
- `inlet(self, body, user)`: Inspect the incoming chat message; if it matches triggers, call the backend and append a formatted response; otherwise pass through.

Backend compatibility expectations:
- Endpoints accept JSON and return structured JSON (`items`, `summary`, `meta` where applicable).
- Non-200 responses should be caught by the pipeline and surfaced as a concise error message.

## Triggers and UX

- Jobs: “find jobs”, “search jobs”, “job hunt”, “linkedin jobs … <role> in <location>”
- Inbox: “check inbox”, “process email”, “email summary”
- Briefing: “daily briefing”, “intelligence update”, “market news”

Pipelines should show a short “working…” notice for long calls and truncate output with a “Show more” link when needed.

## Configuration & security

- Configure via `Valves`; default `smart_assistant_url` is `http://localhost:8000` for local.
- If an API key is required, send `Authorization: Bearer <token>` to the backend.
- Respect user-level rate limits; debounce repeated triggers; use backend `limit` parameters.

## Testing quick start

1) Verify backend is up: GET `/health` should return `{ "status": "ok" }`.
2) Test jobs endpoint: POST `/api/smart-assistant/jobs/search` with `{ "query": "python developer remote", "limit": 5 }`.
3) Enable the pipeline in Open WebUI and send “find python developer jobs”.

## Migration note

Legacy “multi-agent” content was removed in favor of the simpler, reliable pipeline → REST integration used today. For orchestration or RAG, use Open WebUI’s existing features (pipelines, documents, vector DB) instead of custom agent layers.

---

Next: [Data Architecture](./03-data-architecture.md)
