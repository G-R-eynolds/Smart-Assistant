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
    
    # CORS settings
    CORS_ALLOW_ORIGIN: str = os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:5173")
    
    # Security settings
    WEBUI_SECRET_KEY: str = os.getenv("WEBUI_SECRET_KEY", "your-secret-key-change-this-in-production")
    ENABLE_SIGNUP: bool = os.getenv("ENABLE_SIGNUP", "true").lower() == "true"
    DEFAULT_USER_ROLE: str = os.getenv("DEFAULT_USER_ROLE", "user")
    
    # Feature flags
    ENABLE_RAG_CHAT: bool = os.getenv("ENABLE_RAG_CHAT", "true").lower() == "true"
    
    # Smart Assistant settings
    SMART_ASSISTANT_URL: str = os.getenv("SMART_ASSISTANT_URL", "http://localhost:8001")
    
    # LinkedIn Scraper settings
    BRIGHT_DATA_USERNAME: str = os.getenv("BRIGHT_DATA_USERNAME", "")
    BRIGHT_DATA_PASSWORD: str = os.getenv("BRIGHT_DATA_PASSWORD", "")
    BRIGHT_DATA_HOST: str = os.getenv("BRIGHT_DATA_HOST", "brd.superproxy.io")
    BRIGHT_DATA_PORT: int = int(os.getenv("BRIGHT_DATA_PORT", "22225"))

# Create a global instance of settings
settings = Settings()
