# Alembic for Smart Assistant Backend

This directory contains database migration scripts managed by Alembic.

- Configuration: `alembic.ini`
- Environment script: `alembic/env.py`
- Migrations: `alembic/versions/`

Usage (from repo root):

```
backend/.venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m "initial"
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

Alembic uses the DATABASE_URL from `app.core.config.settings`. For SQLite it will
use `sqlite+aiosqlite` automatically.
