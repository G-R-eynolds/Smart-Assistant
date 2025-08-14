## ---------- Frontend Build Stage ----------
FROM node:20-alpine AS frontend_build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build || npm run build --if-present

## ---------- Backend Stage ----------
FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	APP_ENV=production
WORKDIR /app
# Minimal runtime; no extra system packages required
COPY backend/pyproject.toml backend/README.md ./
RUN pip install --no-cache-dir .
COPY backend/app ./app
COPY --from=frontend_build /frontend/dist ./frontend/dist
ENV ENABLE_GRAPHRAG=true
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
