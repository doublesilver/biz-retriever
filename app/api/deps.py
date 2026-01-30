from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db.session import get_db
from app.core.security import get_current_user
from app.services.crawler_service import G2BCrawlerService
from app.db.repositories.bid_repository import BidRepository

def get_crawler_service() -> G2BCrawlerService:
    """
    Dependency Injection for Crawler Service.
    Creates a new instance or returns a shared one depending on lifecycle needs.
    """
    return G2BCrawlerService()

async def get_bid_repository(session: AsyncSession = Depends(get_db)) -> BidRepository:
    """
    Dependency for BidRepository
    """
    return BidRepository(session)
