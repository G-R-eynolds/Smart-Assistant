"""
Logging configuration for the Smart Assistant Backend API.

Provides centralized logging setup and configuration.
"""
import logging
from typing import Optional
import os

def setup_logging(level: Optional[str] = None):
    """
    Set up logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
        
    # Convert string level to logging level constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create a logger for our application
    logger = logging.getLogger("smart_assistant")
    logger.setLevel(numeric_level)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(console_handler)
        
        # Add file handler if log directory exists
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(os.path.join(log_dir, "smart_assistant.log"))
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(file_handler)
    
    return logger

# Create default logger
logger = setup_logging()
