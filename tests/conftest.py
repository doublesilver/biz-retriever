"""
pytest 설정 및 Fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.db.base import Base

# Test Database URL (In-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 DB 세션
    각 테스트마다 새로운 DB 생성
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
def sample_announcement_data():
    """샘플 공고 데이터"""
    return {
        "title": "서울대병원 구내식당 위탁운영",
        "content": "서울대병원 구내식당 위탁운영 입찰 공고",
        "agency": "서울대학교병원",
        "url": "https://example.com/bid/123",
        "source": "G2B",
        "estimated_price": 150000000,
        "keywords_matched": ["구내식당", "위탁운영"]
    }

@pytest.fixture
def exclude_keywords_sample():
    """제외 키워드 샘플"""
    return ["폐기물", "단순공사", "설계용역"]
