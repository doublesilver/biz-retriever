"""
Database Session Configuration

This module provides database session management with automatic environment
detection. In Vercel serverless environments, it uses NullPool for optimal
stateless operation. In traditional environments (e.g., Raspberry Pi), it
uses QueuePool for connection reuse.
"""

import os
from typing import AsyncGenerator

# Detect Vercel serverless environment
if os.getenv("VERCEL") == "1":
    # Serverless mode: Use NullPool for stateless connections
    from app.db.session_serverless import async_session_maker, engine, get_db
else:
    # Traditional mode: Use QueuePool for connection reuse
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from app.core.config import settings

    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=settings.SQL_ECHO,  # Controlled by SQL_ECHO env var (default: False)
        future=True,
        pool_size=3,  # Optimized for Raspberry Pi (4GB RAM, 4 cores)
        max_overflow=5,  # Total 8 connections max
        pool_timeout=30,  # Connection wait timeout (seconds)
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections every hour (prevent memory leaks)
    )

    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency for getting async session (QueuePool mode)
        """
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()


# Backwards compatibility alias
AsyncSessionLocal = async_session_maker
