# Agent Framework Specification

## Overview

This document defines the principles, roles, and interaction patterns for the collaborative multi-agent system that powers the Smart Assistant. The framework is designed using CrewAI to ensure that specialized agents can work together effectively, sharing context and intelligence to accomplish complex user-driven workflows.

## Core Principles

1.  **Single Responsibility**: Each agent has a single, clearly defined purpose and a corresponding set of capabilities. This ensures modularity and maintainability.
2.  **Collaborative Intelligence**: Agents operate within a shared context, enabling them to delegate tasks, share findings, and build upon each other's work.
3.  **Human-in-the-Loop**: All significant AI-driven actions or content generation tasks are subject to user review and approval, ensuring quality and control.
4.  **Cost Awareness**: Agents are designed to be efficient, using intelligent model selection, batching, and caching to minimize API costs.
5.  **Fault Tolerance**: The framework is designed to be resilient. Agents can handle failures gracefully and, where possible, operate with degraded functionality if a dependency is unavailable.

## Agent Roles and Responsibilities

The system is composed of agents with distinct roles, ensuring a clear separation of concerns.

### 1. Orchestrator Agent (`AgentConductor`)
-   **Role**: The central coordinator for all multi-agent workflows.
-   **Responsibilities**:
    -   Receives initial user requests from the API Gateway.
    -   Interprets the user's intent and defines the high-level workflow required.
    -   Selects and sequences the appropriate specialist agents for the task.
    -   Manages the lifecycle of a workflow, tracking its state from initiation to completion.
    -   Facilitates communication and data transfer between agents.
    -   Handles errors and orchestrates recovery or graceful failure of a workflow.

### 2. Specialist Agents
Specialist agents perform the core domain-specific tasks of the system.

-   **`JobAgent`**:
    -   **Purpose**: Manages the job discovery pipeline.
    -   **Responsibilities**: Polls external job boards, standardizes job data, scores jobs against the user's profile, and stores qualified leads.

-   **`EmailAgent`**:
    -   **Purpose**: Provides intelligence for the user's inbox.
    -   **Responsibilities**: Fetches new emails, classifies them by category and priority, extracts key information, and generates summaries.

-   **`ContentAgent`**:
    -   **Purpose**: Assists with the creation of professional documents.
    -   **Responsibilities**: Analyzes target requirements (e.g., a job description), tailors base templates (e.g., a CV), and generates high-quality, context-aware content.

-   **`NewsAgent`**:
    -   **Purpose**: Curates a personalized intelligence briefing.
    -   **Responsibilities**: Aggregates news from various sources, filters content based on user interests, and synthesizes key insights.

## Agent Interaction Patterns

This section defines the standardized patterns for how agents communicate and collaborate.

### 1. Workflow Orchestration
-   **Pattern**: The `AgentConductor` uses a "Director" pattern. It defines a plan (a sequence of tasks) and delegates each task to the appropriate specialist agent.
-   **Example Flow (Job Application)**:
    1.  User requests to apply for a job.
    2.  `AgentConductor` creates a workflow:
        a.  **Task 1**: Delegate to `JobAgent` to retrieve all details for the target job.
        b.  **Task 2**: Delegate to `ContentAgent`, providing the job details and the user's base CV, to generate a tailored CV.
        c.  **Task 3**: Delegate to `ContentAgent` again to draft a cover letter.
    3.  `AgentConductor` collects the results and presents them to the user for approval.

### 2. Task Delegation
-   **Pattern**: A specialist agent can delegate a sub-task to another agent if it requires a capability outside its own.
-   **Example**: While processing an email, the `EmailAgent` might identify a job opportunity mentioned in the text. It would then delegate a task to the `JobAgent` to process and score this opportunity, rather than attempting to do so itself.

### 3. Context Sharing
-   **Mechanism**: All agents have access to the shared `VectorMemorySystem`. Before executing a task, an agent queries this system to retrieve relevant context (e.g., user preferences, recent activities, historical data). After completing a task, it writes back any new, valuable information to the memory system.
-   **Benefit**: This ensures that all agents are working with the most up-to-date and relevant information, leading to more coherent and intelligent outcomes.

## Agent Configuration

-   **Centralized Management**: The core configuration for each agent (e.g., base prompts, model preferences, allowed tools) will be managed in a centralized configuration store (e.g., YAML files or a dedicated database table).
-   **Dynamic Loading**: Configurations will be loaded at runtime, allowing for updates without requiring a full system redeployment.
-   **User Overrides**: The system will support user-specific overrides for certain parameters (e.g., preferred tone for content generation), which will be stored and applied by the `ContextManager`.

## Cost Optimization Framework

The agent framework will incorporate several strategies to manage operational costs, particularly for LLM API calls.

-   **Intelligent Model Selection**: The `AgentConductor` will select the most cost-effective model for a given task based on its complexity. For example, simple classification tasks (`EmailAgent`) will use a faster, cheaper model (e.g., Gemini Flash), while complex content generation (`ContentAgent`) will use a more powerful model (e.g., Gemini Pro).
-   **Request Batching**: Agents will be designed to batch multiple items into a single API request where possible (e.g., scoring multiple jobs at once).
-   **Intelligent Caching**: Results from expensive API calls will be cached (e.g., in Redis). Before making a new request, an agent will first check if a sufficiently fresh result already exists in the cache.

---

**Next**: Review [Data Architecture](./03-data-architecture.md) for database design and vector memory management.

### Batch Processing Optimization
```python
class BatchOptimizer:
    def __init__(self, max_batch_size: int = 20):
        self.max_batch_size = max_batch_size
        self.batch_accumulator = defaultdict(list)
    
    async def add_to_batch(self, agent_name: str, task: AgentTask):
        """Add task to batch for processing"""
        self.batch_accumulator[agent_name].append(task)
        
        if len(self.batch_accumulator[agent_name]) >= self.max_batch_size:
            await self._process_batch(agent_name)
    
    async def _process_batch(self, agent_name: str):
        """Process accumulated batch"""
        tasks = self.batch_accumulator[agent_name]
        self.batch_accumulator[agent_name] = []
        
        agent = self.agents[agent_name]
        results = await agent.process_batch(tasks)
        
        for task, result in zip(tasks, results):
            await self._notify_completion(task.id, result)
```

---

**Next**: Review [Data Architecture](./03-data-architecture.md) for vector database design and data management patterns.
