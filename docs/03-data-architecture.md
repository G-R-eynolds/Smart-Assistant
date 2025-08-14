# Data Architecture

## Overview

The backend uses a relational database managed via SQLAlchemy (async) with Alembic migrations. SQLite (with `aiosqlite`) is the default for development; Postgres/Redis are optional via Docker profiles. Open WebUI may provide RAG separately; this backend does not require a vector DB.

## Storage

- Engine: `sqlite+aiosqlite` in dev, configurable via `DATABASE_URL`
- Migrations: Alembic under `backend/alembic/`
- Lifecycle: DB init/close wired in `app.main` lifespan

## Initial Schema (Alembic 390308ac594c)

- `users`: id, username, email, full_name, role, hashed_password, is_active, created_at, updated_at
- `career_profiles`: id, user_id → users.id, job_title, skills (JSON), experience_years, education (JSON), preferred_locations (JSON), resume_text (Text), created_at, updated_at
- `processed_job_urls`: id (int, autoinc), url (unique), job_title, company, created_at, updated_at
- `job_opportunities`: id, user_id → users.id, title, company, location, description (Text), url, salary_range, employment_type, source, relevance_score (Float), ai_insights (JSON), status, date_applied, airtable_record_id, created_at, updated_at
- `email_processing_history`: id, user_id → users.id, email_count, important_count, processed_at, summary (Text), created_at, updated_at
- `intelligence_briefings`: id, user_id → users.id, title, date, content (JSON), read_status (Bool), created_at, updated_at
- `job_search_configs`: id, user_id → users.id, preferred_job_types (JSON), min_salary, max_commute_distance, industries (JSON), exclude_keywords (JSON), airtable_api_key, airtable_base_id, airtable_table_name, created_at, updated_at

## Notes

- Dedup table prevents reprocessing job URLs across runs.
- If enabling Postgres, ensure Alembic upgrade runs on startup.
- Keep PII minimal; add encryption only when storing sensitive data.

---

Next: [API Design](./04-api-design.md).
