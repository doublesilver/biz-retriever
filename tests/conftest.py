"""
pytest 설정 및 Fixtures
"""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
# FastAPICache for testing
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db import session as db_session_module
from app.db.base import Base
from app.db.models import BidAnnouncement, User
from app.main import app

# Test Database URL (In-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def init_cache():
    """테스트용 인메모리 캐시 초기화"""
    FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    yield
    await FastAPICache.clear()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 DB 세션
    각 테스트마다 새로운 DB 생성하고 dependency override 설정
    StaticPool을 사용하여 모든 연결이 같은 인메모리 DB를 공유
    """
    # StaticPool로 모든 연결이 같은 in-memory DB 공유
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False, poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Dependency override 함수
    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    # Override 적용
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[db_session_module.get_db] = override_get_db

    async with test_session_maker() as session:
        yield session

    # Cleanup
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def sample_announcement_data():
    """샘플 공고 데이터"""
    return {
        "title": "서울대병원 구내식당 위탁운영",
        "content": "서울대병원 구내식당 위탁운영 입찰 공고입니다.",
        "agency": "서울대학교병원",
        "url": "https://example.com/bid/123",
        "source": "G2B",
        "estimated_price": 150000000,
        "keywords_matched": ["구내식당", "위탁운영"],
        "posted_at": datetime.utcnow(),
        "deadline": datetime.utcnow() + timedelta(days=7),
        "importance_score": 2,
    }


@pytest.fixture
def exclude_keywords_sample():
    """제외 키워드 샘플"""
    return ["폐기물", "단순공사", "설계용역"]


# ============================================
# 사용자 및 인증 관련 Fixtures
# ============================================


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """테스트용 사용자 생성"""
    user = User(
        email="test@example.com", hashed_password=get_password_hash("TestPass123!"), is_active=True, is_superuser=False
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_superuser(test_db: AsyncSession) -> User:
    """테스트용 슈퍼유저 생성"""
    user = User(
        email="admin@example.com", hashed_password=get_password_hash("AdminPass123!"), is_active=True, is_superuser=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """인증 토큰 생성"""
    return create_access_token(subject=test_user.email)


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """인증 헤더"""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================
# 샘플 공고 Fixtures
# ============================================


@pytest.fixture
async def sample_bid(test_db: AsyncSession, sample_announcement_data: dict) -> BidAnnouncement:
    """DB에 저장된 샘플 공고"""
    bid = BidAnnouncement(
        title=sample_announcement_data["title"],
        content=sample_announcement_data["content"],
        agency=sample_announcement_data["agency"],
        url=sample_announcement_data["url"],
        source=sample_announcement_data["source"],
        estimated_price=sample_announcement_data["estimated_price"],
        keywords_matched=sample_announcement_data["keywords_matched"],
        posted_at=sample_announcement_data["posted_at"],
        deadline=sample_announcement_data["deadline"],
        importance_score=sample_announcement_data["importance_score"],
    )
    test_db.add(bid)
    await test_db.commit()
    await test_db.refresh(bid)
    return bid


@pytest.fixture
async def multiple_bids(test_db: AsyncSession) -> list:
    """여러 개의 테스트 공고 생성"""
    bids = []
    for i in range(5):
        bid = BidAnnouncement(
            title=f"테스트 공고 {i+1}",
            content=f"테스트 내용 {i+1}",
            agency=f"테스트 기관 {i % 3 + 1}",  # 3개 기관 순환
            url=f"https://example.com/bid/{i+1}",
            source="G2B" if i % 2 == 0 else "Onbid",
            estimated_price=100000000 + i * 10000000,
            posted_at=datetime.utcnow() - timedelta(days=i),
            deadline=datetime.utcnow() + timedelta(days=7 - i),
            importance_score=(i % 3) + 1,  # 1, 2, 3 순환
            keywords_matched=["키워드1", "키워드2"] if i % 2 == 0 else [],
        )
        test_db.add(bid)
        bids.append(bid)

    await test_db.commit()
    for bid in bids:
        await test_db.refresh(bid)

    return bids


# ============================================
# Mock Fixtures
# ============================================


@pytest.fixture
def mock_redis():
    """Redis Mock"""
    mock_redis = AsyncMock()
    mock_redis.sadd = AsyncMock(return_value=1)
    mock_redis.smembers = AsyncMock(return_value={b"keyword1", b"keyword2"})
    mock_redis.srem = AsyncMock(return_value=1)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    return mock_redis


@pytest.fixture
def mock_celery_task():
    """Celery Task Mock"""
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    mock_task.state = "PENDING"
    mock_task.ready.return_value = False
    mock_task.result = None
    return mock_task


@pytest.fixture
def mock_httpx_client():
    """HTTPX AsyncClient Mock"""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_slack_webhook():
    """Slack Webhook Mock"""
    with patch("app.services.notification_service.httpx.AsyncClient") as mock:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_instance.post = AsyncMock(return_value=mock_response)

        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_g2b_api():
    """G2B API Mock"""
    with patch("app.services.crawler_service.httpx.AsyncClient") as mock:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "테스트 구내식당 위탁운영",
                            "bidNtceDtl": "테스트 공고 상세 내용",
                            "ntceInsttNm": "테스트 기관",
                            "bidNtceDt": "202501201000",
                            "bidClseDt": "202501271800",
                            "bidNtceUrl": "https://g2b.example.com/bid/1",
                            "presmptPrce": "100000000",
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)

        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_openai():
    """OpenAI API Mock"""
    with patch("app.services.rag_service.ChatOpenAI") as mock:
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "테스트 요약 결과입니다. 주요 키워드: 테스트, 입찰, 공고"
        mock_llm.apredict_messages = AsyncMock(return_value=mock_response)

        mock.return_value = mock_llm
        yield mock


# ============================================
# HTTP Client Fixtures
# ============================================


@pytest.fixture
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 클라이언트 (인증 없음) - test_db 의존으로 dependency override 활성화"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_client(test_user: User, test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """인증된 비동기 HTTP 클라이언트 - test_db, test_user 의존"""
    token = create_access_token(subject=test_user.email)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client


# ============================================
# 크롤러 서비스 Fixtures
# ============================================


@pytest.fixture
def crawler_service():
    """G2B 크롤러 서비스 인스턴스"""
    from app.services.crawler_service import G2BCrawlerService

    return G2BCrawlerService()


@pytest.fixture
def notification_service():
    """Slack 알림 서비스 인스턴스"""
    from app.services.notification_service import SlackNotificationService

    return SlackNotificationService()


@pytest.fixture
def rag_service():
    """RAG 서비스 인스턴스"""
    from app.services.rag_service import RAGService

    return RAGService()


@pytest.fixture
def ml_service():
    """ML 서비스 인스턴스"""
    from app.services.ml_service import MLService

    return MLService()


@pytest.fixture
def file_service():
    """파일 서비스 인스턴스"""
    from app.services.file_service import FileService

    return FileService()
