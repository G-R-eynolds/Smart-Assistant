"""
Database connection management.

Provides asynchronous database connection and session handling using SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from app.models.database import Base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine based on the DATABASE_URL in settings
engine = None
async_session = None

async def init_db():
    """Initialize the database connection."""
    global engine, async_session
    
    database_url = settings.DATABASE_URL
    
    # Convert sqlite URL to aiosqlite for async support if needed
    if database_url.startswith('sqlite:'):
        database_url = database_url.replace('sqlite:', 'sqlite+aiosqlite:')
    
    logger.info(f"Initializing database connection to {database_url.split('@')[0]}...")
    
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    
    # Create async session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")

async def close_db():
    """Close the database connection."""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    if async_session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
