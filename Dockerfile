FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

WORKDIR /app

# Install dependencies
COPY backend/pyproject.toml backend/README.md ./
RUN pip install --no-cache-dir .

# Copy application code
COPY backend/app ./app

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
