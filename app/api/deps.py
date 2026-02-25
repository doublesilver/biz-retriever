"""
Dependency Injection Layer

FastAPI Annotated 패턴을 사용한 표준화된 DI 시스템:
- 타입 별칭으로 재사용성 향상
- IDE 자동완성 지원
- 테스트 시 Mock 주입 용이
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import User
from app.db.repositories.bid_repository import BidRepository
from app.db.session import get_db
from app.services.crawler_service import G2BCrawlerService
from app.services.notification_service import NotificationService
from app.services.rag_service import RAGService

# ============================================
# Database Session
# ============================================

DbSession = Annotated[AsyncSession, Depends(get_db)]
"""
Database Session Dependency

Usage:
    @router.get("/items")
    async def list_items(session: DbSession):
        ...
"""


# ============================================
# Authentication
# ============================================

CurrentUser = Annotated[User, Depends(get_current_user)]
"""
Current Authenticated User

Usage:
    @router.get("/profile")
    async def get_profile(user: CurrentUser):
        return {"email": user.email}
"""


# ============================================
# Repositories
# ============================================


def get_bid_repository(session: DbSession) -> BidRepository:
    """Bid Repository Factory"""
    return BidRepository(session)


BidRepo = Annotated[BidRepository, Depends(get_bid_repository)]
"""
Bid Repository Dependency

Usage:
    @router.get("/bids/{bid_id}")
    async def get_bid(bid_id: int, repo: BidRepo):
        return await repo.get_by_id(bid_id)
"""


# ============================================
# Services
# ============================================


def get_crawler_service() -> G2BCrawlerService:
    """G2B Crawler Service Factory"""
    return G2BCrawlerService()


CrawlerService = Annotated[G2BCrawlerService, Depends(get_crawler_service)]
"""
G2B Crawler Service Dependency

Usage:
    @router.post("/crawl")
    async def trigger_crawl(crawler: CrawlerService):
        await crawler.fetch_new_announcements()
"""


def get_rag_service() -> RAGService:
    """RAG (AI Analysis) Service Factory"""
    return RAGService()


RagService = Annotated[RAGService, Depends(get_rag_service)]
"""
RAG/AI Analysis Service Dependency

Usage:
    @router.post("/analyze")
    async def analyze_bid(content: str, rag: RagService):
        return await rag.analyze_bid(content)
"""


def get_notification_service() -> NotificationService:
    """Notification Service Factory"""
    return NotificationService()


NotifService = Annotated[NotificationService, Depends(get_notification_service)]
"""
Notification Service Dependency

Usage:
    @router.post("/notify")
    async def send_notification(notif: NotifService):
        await notif.send_slack_message("Hello")
"""
