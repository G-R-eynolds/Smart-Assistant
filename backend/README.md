# Smart Assistant Backend

This is the unified backend for the Smart Assistant project, combining functionality from multiple previous backends. It provides job discovery, inbox management, and intelligence briefing capabilities.

## Features

- **Job Discovery API**: Find relevant job opportunities using AI-powered matching
- **Inbox Management**: Process and categorize email inboxes
- **Intelligence Briefing**: Generate personalized daily briefings with market insights and career information
- **PostgreSQL Database**: Stores user data, job opportunities, and application tracking
- **Vector Search**: Uses Qdrant for semantic search capabilities

## Development Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the development server:
```bash
./dev.sh
```

## Project Structure

```
backend/
├── app/                  # Main application package
│   ├── api/              # API routers
│   │   └── smart_assistant.py
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   └── database.py   # Database connection
│   ├── functions/        # Business logic functions
│   │   ├── job_discovery.py
│   │   ├── inbox_management.py
│   │   └── intelligence_briefing.py
│   ├── models/           # Database models
│   └── main.py           # Application entrypoint
├── tests/                # Test suite
├── .env.example          # Example environment variables
├── .env                  # Environment variables (not in version control)
├── dev.sh                # Development startup script
└── pyproject.toml        # Python project configuration
```

## Testing

Run tests using pytest:

```bash
pytest
```

## API Endpoints

The backend provides the following API endpoints:

- `GET /api/smart-assistant/health`: Health check endpoint
- `POST /api/smart-assistant/job-discovery/run`: Run job discovery pipeline
- `POST /api/smart-assistant/inbox/process`: Process email inbox
- `POST /api/smart-assistant/briefing/generate`: Generate intelligence briefing

## Docker Support

The backend can be run in Docker using the provided Dockerfile and docker-compose.yml:

```bash
# Start just the database services
docker-compose up -d postgres qdrant redis

# Or start the complete stack
docker-compose up -d
```

## Environment Variables

The most important environment variables are:

- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_URL`: Qdrant vector database URL
- `OPENAI_API_KEY`: OpenAI API key for AI functionality
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `PORT`: Port to run the server on (default: 8080)

For a complete list, see the `.env.example` file.

Run the test suite:
```bash
pytest
```

## Project Structure

- `app/`: Main application package
  - `api/`: FastAPI routers
  - `core/`: Core services (AI, DB, etc.)
  - `models/`: Database models
  - `schemas/`: Pydantic schemas
  - `functions/`: Pipeline functions
  - `main.py`: FastAPI app entrypoint
- `tests/`: All Python tests
