from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.SQL_ECHO,  # Controlled by SQL_ECHO env var (default: False)
    future=True,
    pool_size=20,  # Connection pool for production
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
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
