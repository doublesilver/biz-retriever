from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

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

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting async session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
