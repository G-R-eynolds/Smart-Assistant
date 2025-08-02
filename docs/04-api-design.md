# API Design Specification

## Overview

This document defines the API architecture for the Smart Assistant. The system exposes a multi-faceted API that includes a primary **RESTful interface** for standard resource management, a **GraphQL endpoint** for complex data queries, and a **WebSocket connection** for real-time, bidirectional communication. This hybrid approach ensures flexibility, performance, and a rich developer experience.

## Core Principles

1.  **REST for Simplicity**: Utilize standard RESTful conventions (HTTP verbs, status codes, resource-based URLs) for all primary create, read, update, and delete (CRUD) operations.
2.  **GraphQL for Flexibility**: Provide a GraphQL endpoint to allow clients to request exactly the data they need, reducing over-fetching and enabling complex data aggregation in a single request.
3.  **WebSockets for Real-Time**: Use WebSockets to push real-time updates from the server to the client (e.g., task completions, new job alerts) without the need for polling.
4.  **Security First**: All API endpoints are protected through robust authentication and authorization mechanisms. Access is granted on a need-to-know basis using scoped permissions.
5.  **Clear Versioning**: The API is versioned (e.g., `/api/v1/`) to allow for future changes without breaking existing client integrations.

## API Architecture

### 1. RESTful API
-   **Purpose**: The workhorse for all standard interactions with the system's resources.
-   **Structure**: Follows a logical, resource-oriented structure (e.g., `/users`, `/jobs`, `/agents`).
-   **Authentication**: All requests must be authenticated using a JSON Web Token (JWT) passed in the `Authorization` header.

### 2. GraphQL Endpoint
-   **Purpose**: To serve complex queries from the front-end application, allowing it to fetch nested data from multiple resources in a single API call.
-   **Endpoint**: A single endpoint (e.g., `/graphql`) handles all GraphQL queries and mutations.
-   **Use Cases**: Ideal for dashboards, detailed views, and analytics that require data from various parts of the system.

### 3. WebSocket API
-   **Purpose**: To provide a persistent, low-latency connection for real-time updates.
-   **Endpoint**: A dedicated WebSocket endpoint (e.g., `/ws`) manages connections.
-   **Use Cases**: Pushing notifications for new job discoveries, agent task status changes, and when a new daily briefing is ready.

## Security & Access Control

-   **Authentication**: The system uses **JWT-based authentication**. Users log in with credentials to receive a short-lived access token, which must be included in all subsequent API requests.
-   **Authorization**: Access to resources is governed by a **scope-based system**. Tokens are issued with specific permissions (e.g., `jobs:read`, `content:create`), and endpoints will reject requests from tokens that lack the required scope.
-   **Rate Limiting**: To ensure system stability and fair usage, the API implements rate limiting based on the user's subscription tier and IP address.
-   **Quota Management**: In addition to rate limiting, resource-intensive operations (like requests to the AI models) are subject to monthly quotas based on the user's plan.

## REST API Endpoint Definitions

The following is a high-level overview of the available RESTful resources and their primary functions.

### `/auth`
-   **Purpose**: Handles user authentication.
-   `POST /token`: Exchange user credentials for a JWT access token.

### `/users`
-   **Purpose**: Manages user accounts and their associated profiles and preferences.
-   `GET /users/me`: Retrieve the profile of the currently authenticated user.
-   `PUT /users/me`: Update the profile of the currently authenticated user.
-   `GET /users/me/preferences`: Retrieve the user's application preferences.
-   `PUT /users/me/preferences`: Update the user's application preferences.

### `/agents`
-   **Purpose**: Manages and interacts with the AI agents.
-   `POST /agents/tasks`: Submit a new asynchronous task to a specified agent (e.g., "find new jobs").
-   `GET /agents/tasks/{task_id}`: Check the status and retrieve the results of a previously submitted task.
-   `GET /agents/status`: Get the current operational status and load of all agents.

### `/jobs`
-   **Purpose**: Manages the job opportunities discovered for the user.
-   `GET /jobs`: Retrieve a list of jobs, with support for filtering by status, location, etc.
-   `GET /jobs/{job_id}`: Get the detailed information for a single job.
-   `PUT /jobs/{job_id}`: Update the status of a job (e.g., from 'new' to 'applied').

### `/content`
-   **Purpose**: Manages the generation of personalized content.
-   `POST /content/generate`: Request the `ContentAgent` to generate content, such as a tailored CV for a specific job.
-   `GET /content/history`: Retrieve a log of previously generated content.

### `/briefings`
-   **Purpose**: Manages the creation and retrieval of user briefings.
-   `GET /briefings/latest`: Retrieve the most recent daily briefing for the user.
-   `GET /briefings/{briefing_id}`: Retrieve a specific briefing by its ID.

### `/memories`
-   **Purpose**: Provides an interface to the system's semantic memory.
-   `GET /memories/search`: Perform a semantic search across the user's memories using a natural language query.
-   `POST /memories`: Manually add a new piece of information to the user's memory.

## External Integrations (Webhooks)

-   **Purpose**: To receive real-time updates from external services.
-   `POST /webhooks/gmail`: An endpoint designed to receive push notifications from the Gmail API when a new email arrives for the user. This triggers the `EmailAgent`.
-   **Security**: All webhook endpoints are secured and must be registered with the external service. Incoming requests are verified to ensure they originate from the trusted source.

## API Documentation

The entire API, including the REST, GraphQL, and WebSocket interfaces, will be formally documented using the **OpenAPI specification**. This documentation will be made available to developers through an interactive web UI (e.g., Swagger UI), providing clear examples, schema definitions, and a way to test endpoints directly from the browser.

---

**Next**: Review [Epic 1: Job Opportunity Pipeline](./05-job-pipeline.md) for detailed job discovery and management workflows.
