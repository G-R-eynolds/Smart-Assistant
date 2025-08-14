"""
Core configuration settings for Smart Assistant backend.

Centralizes all configuration settings using environment variables and provides
defaults where appropriate.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    logger.info(f"Loading environment from {env_path}")
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        logger.warning(f"Error loading .env file: {e}")

class Settings:
    """Application settings loaded from environment variables"""
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/webui.db")
    
    # API settings
    ENABLE_OPENAI_API: bool = os.getenv("ENABLE_OPENAI_API", "true").lower() == "true"
    ENABLE_OLLAMA_API: bool = os.getenv("ENABLE_OLLAMA_API", "false").lower() == "true"
    OPENAI_API_BASE_URL: str = os.getenv("OPENAI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Gemini API settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # CV and Cover Letter settings
    CV_DIRECTORY: str = os.getenv("CV_DIRECTORY", "/home/gabe/Documents/Agent Project 2.0/backend/data/cv")
    CV_FILENAME: str = os.getenv("CV_FILENAME", "cv.pdf")
    COVER_LETTER_STYLE_PROMPT: str = os.getenv("COVER_LETTER_STYLE_PROMPT", 
        "Write a professional, engaging cover letter that is concise yet comprehensive. "
        "The tone should be confident but not arrogant, enthusiastic but professional. "
        "Focus on relevant experience and skills that match the job requirements. "
        "Keep it to 3-4 paragraphs maximum. Avoid generic phrases and make it specific to the role.")
    
    # CORS settings
    CORS_ALLOW_ORIGIN: str = os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:5173")
    
    # Security settings
    WEBUI_SECRET_KEY: str = os.getenv("WEBUI_SECRET_KEY", "your-secret-key-change-this-in-production")
    ENABLE_SIGNUP: bool = os.getenv("ENABLE_SIGNUP", "true").lower() == "true"
    DEFAULT_USER_ROLE: str = os.getenv("DEFAULT_USER_ROLE", "user")
    
    # Feature flags
    ENABLE_RAG_CHAT: bool = os.getenv("ENABLE_RAG_CHAT", "true").lower() == "true"
    ENABLE_GRAPHRAG: bool = os.getenv("ENABLE_GRAPHRAG", "true").lower() == "true"
    GRAPHRAG_API_KEY: str = os.getenv("GRAPHRAG_API_KEY", "")
    # Prefer Gemini-native structured search over official library even if available
    GRAPHRAG_FORCE_GEMINI_STRUCTURED: bool = os.getenv("GRAPHRAG_FORCE_GEMINI_STRUCTURED", "true").lower() == "true"
    # Phase 6 flag: legacy|graphrag (determines default ingestion path for new docs)
    DEFAULT_INGEST_MODE: str = os.getenv("DEFAULT_INGEST_MODE", "graphrag")  # legacy|graphrag
    
    # GraphRAG & Vector settings
    GRAPH_STORE: str = os.getenv("GRAPH_STORE", "sqlite")  # sqlite|neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")  # optional, if vector DB is available
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai|none
    MULTI_TENANT: bool = os.getenv("MULTI_TENANT", "false").lower() == "true"
    DEFAULT_NAMESPACE: str = os.getenv("DEFAULT_NAMESPACE", "public")
    # Index orchestrator schedule (seconds); 0 disables
    INDEX_SCHEDULE_INTERVAL_SECONDS: int = int(os.getenv("INDEX_SCHEDULE_INTERVAL_SECONDS", "0"))
    # Cluster summarization budgeting
    CLUSTER_SUMMARY_DAILY_TOKEN_BUDGET: int = int(os.getenv("CLUSTER_SUMMARY_DAILY_TOKEN_BUDGET", "20000"))
    CLUSTER_SUMMARY_MAX_TOKENS_PER: int = int(os.getenv("CLUSTER_SUMMARY_MAX_TOKENS_PER", "180"))
    CLUSTER_SUMMARY_RATE_LIMIT_PER_MIN: int = int(os.getenv("CLUSTER_SUMMARY_RATE_LIMIT_PER_MIN", "15"))
    
    # Smart Assistant settings
    SMART_ASSISTANT_URL: str = os.getenv("SMART_ASSISTANT_URL", "http://localhost:8001")
    
    # LinkedIn Scraper settings
    BRIGHT_DATA_USERNAME: str = os.getenv("BRIGHT_DATA_USERNAME", "")
    BRIGHT_DATA_PASSWORD: str = os.getenv("BRIGHT_DATA_PASSWORD", "")
    BRIGHT_DATA_HOST: str = os.getenv("BRIGHT_DATA_HOST", "brd.superproxy.io")
    BRIGHT_DATA_PORT: int = int(os.getenv("BRIGHT_DATA_PORT", "22225"))
    BRIGHT_DATA_ENDPOINT: str = os.getenv("BRIGHT_DATA_ENDPOINT", "")
    
    # Airtable settings
    AIRTABLE_API_KEY: str = os.getenv("AIRTABLE_API_KEY", "")
    AIRTABLE_BASE_ID: str = os.getenv("AIRTABLE_BASE_ID", "")
    AIRTABLE_TABLE_NAME: str = os.getenv("AIRTABLE_TABLE_NAME", "Jobs")

# Create a global instance of settings
settings = Settings()
