Part 1: Job Scraping & Analysis Pipeline
This part focuses on connecting your existing LinkedIn scraper to the chat interface and storing the results in Airtable.

Step 1.1: Backend - Create API Endpoint for Job Scraping
Prompt: "In smart_assistant.py, create a new FastAPI endpoint /jobs/search. This endpoint should accept a POST request with a JSON body containing keywords, location, experience_level, job_type, date_posted, and limit. It should then call the search_jobs method from the linkedin_scraper_v2 instance. For now, make the endpoint asynchronous and have it return the scraped job data directly as a JSON response. Ensure you handle potential exceptions from the scraper and return appropriate HTTP error codes."

Step 1.2: Backend - Airtable Integration
Prompt: "Create a new file backend/app/core/airtable_client.py. In this file, implement a class AirtableClient to interact with the Airtable API. It should have methods for __init__ (to set up the API key, base ID, and table name from settings), and a method add_jobs(jobs: List[Dict]). The add_jobs method should take a list of job dictionaries and add them as new records to the specified Airtable table. Use the pyairtable library. Add the necessary Airtable configuration variables (AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME) to config.py."

Step 1.3: Backend - Connect Scraper to Airtable
Prompt: "Modify the /jobs/search endpoint in smart_assistant.py. After successfully scraping the jobs, instead of returning the data directly, call the add_jobs method from the AirtableClient to save the jobs to Airtable. The endpoint should then return a confirmation message to the user, like 'Successfully scraped X jobs and saved them to Airtable.' You might want to make this an asynchronous background task so the user gets an immediate response."

Step 1.4: Frontend - Implement Chat Command
Prompt: "In the frontend Svelte application, create a new chat command /find_jobs. When a user types /find_jobs <query>, parse the query to extract parameters like keywords, location, etc. For example, /find_jobs software engineer in "New York". Then, make a POST request to the /api/jobs/search endpoint on the backend with the parsed parameters. Display a message to the user indicating that the job search has started."

Part 2: GraphRAG System for Knowledge Management
This part covers the implementation of the GraphRAG system for indexing and querying documents.

Step 2.1: Infrastructure - Add Neo4j Database
Prompt: "Update the docker-compose.yml file to include a new service for a Neo4j graph database. Configure it with a persistent volume for the data. Expose the necessary ports (7474 for the browser and 7687 for the Bolt driver). Add the Neo4j connection details (URI, user, password) to the backend configuration in config.py."

Step 2.2: Backend - Document Ingestion Pipeline
Prompt: "Create a new module backend/app/core/graph_rag.py. In this module, implement a class GraphRAGIngestor. This class will need a method that can take a text document as input. This method should use a powerful LLM (like Gemini via its API) to extract entities (like people, places, topics) and the relationships between them from the text. The extracted entities should become nodes in the graph, and the relationships should become edges. Use the neo4j Python driver to connect to the Neo4j database and store these nodes and relationships."

Step 2.3: Backend - Query Engine
Prompt: "In backend/app/core/graph_rag.py, add a query method to the GraphRAGIngestor class (or a new GraphRAGQuery class). This method will take a natural language question from the user. It will use an LLM to convert this question into a Cypher query for Neo4j. The method will then execute the Cypher query against the graph database to retrieve relevant context. Finally, it will take this retrieved context, combine it with the original question in a new prompt, and get a final, synthesized answer from the LLM."

Step 2.4: Backend - API for GraphRAG
Prompt: "Create a new API endpoint in smart_assistant.py at /graph/query. This endpoint will accept a POST request with a user's question. It will use the GraphRAG query engine you created in the previous step to get an answer and return it to the frontend."

Step 2.5: Frontend - Integrate GraphRAG into Chat
Prompt: "Update the frontend chat interface. When a user asks a question that isn't a specific command (like /find_jobs), send it to the new /api/graph/query endpoint. Display the answer returned by the GraphRAG system in the chat window."

Part 3: UI Cleanup and Feature Integration
This part focuses on improving the user interface to accommodate the new features.

Step 3.1: Frontend - Job Results Display
Prompt: "Create a new Svelte component to display job search results. When the /find_jobs command is used, and the backend confirms the jobs have been saved to Airtable, provide the user with a link to the Airtable base. The component could show a summary card with the number of jobs found and the link."

Step 3.2: Frontend - Knowledge Graph Visualization Tab
Prompt: "Create a new route and page in the SvelteKit application at /graph. On this page, use a graph visualization library like vis-network or d3.js to display the knowledge graph from the Neo4j database. You will need a new backend endpoint that fetches and returns the graph data (nodes and edges) in a format the frontend library can understand."

Step 3.3: UI/UX - General Cleanup
Prompt: "Review the overall UI of the application. Consolidate the new features into a logical navigation structure. For example, add a 'Tools' or 'Features' section to the main navigation that links to the Job Scraper and the Knowledge Graph visualization. Ensure the design is clean, modern, and consistent across all pages."