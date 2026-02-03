"""
Serverless Database Session Configuration (NullPool)

This module provides database session management optimized for serverless
environments like Vercel. Uses NullPool instead of QueuePool because:

1. Serverless functions are stateless - each request may get a new container
2. Connection pooling wastes resources since connections can't be reused
   across cold starts
3. NullPool creates fresh connections per request, optimal for serverless

For Neon Postgres, use `?pgbouncer=true` in the connection string to enable
server-side connection pooling.
"""

import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum retry attempts for database connection
MAX_RETRIES = 3
# Base delay for exponential backoff (seconds)
BASE_DELAY = 0.5


def get_database_url() -> str:
    """
    Get database URL with Neon pooler configuration if applicable.
    Adds pgbouncer=true for Neon Postgres connections.
    """
    url = settings.SQLALCHEMY_DATABASE_URI
    
    # Add pgbouncer=true for Neon connections if not already present
    if "neon" in url.lower() and "pgbouncer=true" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}pgbouncer=true"
    
    return url


# NullPool for serverless - no persistent connections
engine = create_async_engine(
    get_database_url(),
    poolclass=NullPool,  # No connection pooling - create fresh connections
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.SQL_ECHO,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_with_retry() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session with exponential backoff retry logic.
    
    Retries connection attempts with exponential backoff to handle
    transient failures common in serverless environments (cold starts,
    connection limits, etc.).
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            async with async_session_maker() as session:
                try:
                    yield session
                    return
                finally:
                    await session.close()
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Database connection attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Database connection failed after {MAX_RETRIES} attempts: {e}"
                )
    
    if last_exception:
        raise last_exception


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async session.
    
    This is the primary entry point for database access in serverless mode.
    Uses retry logic to handle transient connection failures.
    """
    async for session in get_db_with_retry():
        yield session
