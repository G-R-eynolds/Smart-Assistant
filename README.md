# Smart Assistant Project

This project integrates AI-powered job discovery, inbox management, and intelligence briefing capabilities into the Open WebUI framework. It provides an intelligent assistant that can find job opportunities, manage email inboxes, and generate daily intelligence briefings.

## Project Structure

The repository is organized as a monorepo with the following structure:

- `/frontend`: SvelteKit frontend application (from Open WebUI)
- `/backend`: FastAPI backend application
- `/docs`: Project documentation and specifications
- `/scripts`: Utility and build scripts
- `/docker-compose.yml`: Docker configuration for development services

## Features

- **Job Discovery**: Smart search and matching for job opportunities
- **Inbox Management**: Email categorization and prioritization
- **Intelligence Briefing**: Daily updates on industry trends, news, and job market insights

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker and Docker Compose (optional, for database services)

### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the development server:
```bash
./dev.sh
```

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend should now be running at http://localhost:5173

### Docker Development Environment

You can start all the required services (PostgreSQL, Qdrant, Redis) using:

```bash
docker-compose up -d
```

This will provide:
- PostgreSQL at `localhost:5432`
- Qdrant vector database at `localhost:6333`
- Redis cache at `localhost:6379`

## Testing

Run the test suite with:

```bash
cd backend
pytest
```

## Documentation

Detailed documentation is available in the `/docs` directory:

- [System Architecture](./docs/01-system-architecture.md)
- [Agent Framework](./docs/02-agent-framework.md)
- [Data Architecture](./docs/03-data-architecture.md)
- [API Design](./docs/04-api-design.md)
- [Job Pipeline](./docs/05-job-pipeline.md)
- [Inbox Management](./docs/06-inbox-management.md)
- [Intelligence Briefing](./docs/07-intelligence-briefing.md)
- [Deployment Guide](./docs/08-deployment-guide.md)
- [Security Guide](./docs/09-security-guide.md)
- [Testing Guide](./docs/10-testing-guide.md)

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

## Docker Compose

For local development with all services:

```bash
docker-compose up
```

## Documentation

See the `/docs` directory for detailed documentation on the system architecture, API design, and development guides.
