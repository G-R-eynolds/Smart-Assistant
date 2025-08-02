"""
Smart Assistant Backend API

Main FastAPI application for the Smart Assistant backend, integrating job discovery, 
inbox management, and intelligence briefing functionality.
"""
import asyncio
import logging
import os
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import core modules
from app.core.config import settings

# Import API routers
from app.api.smart_assistant import router as smart_assistant_router

# Setup logging
logger = logging.getLogger("smart_assistant")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database and other resources
    logger.info("Starting Smart Assistant Backend API")
    # Initialize database here if needed
    
    yield
    
    # Shutdown: Close connections and cleanup
    logger.info("Shutting down Smart Assistant Backend API")
    # Close database connections here if needed

# Create FastAPI application
app = FastAPI(
    title="Smart Assistant API",
    description="API for Smart Assistant functionality including job discovery, inbox management, and intelligence briefing",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(smart_assistant_router, prefix="/api/smart-assistant", tags=["Smart Assistant"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "app": "Smart Assistant Backend API",
        "version": "1.0.0",
        "status": "running",
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
