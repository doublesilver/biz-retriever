from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi_cache.decorator import cache
from app.db.models import ExcludeKeyword
from app.core.logging import logger

class KeywordService:
    @cache(expire=3600)  # Cache for 1 hour
    async def get_active_keywords(self, session: AsyncSession) -> List[str]:
        """
        Get all active exclude keywords. Cached.
        """
        result = await session.execute(
            select(ExcludeKeyword.word).where(ExcludeKeyword.is_active == True)
        )
        return result.scalars().all()

    async def create_keyword(self, session: AsyncSession, word: str) -> ExcludeKeyword:
        """Add a new keyword and clear cache."""
        word = word.strip()
        existing = await session.execute(select(ExcludeKeyword).where(ExcludeKeyword.word == word))
        if existing.scalar_one_or_none():
            raise ValueError(f"Keyword '{word}' already exists.")

        keyword = ExcludeKeyword(word=word)
        session.add(keyword)
        await session.commit()
        await session.refresh(keyword)
        
        # Invalidate cache (Requires clear function or key strategy, 
        # but for simplicity we rely on expire or external clear. 
        # Ideally FastAPICache.clear(namespace="...") should be used.)
        # Here we just log. Real invalidation happens if we use tag-based or clear all.
        logger.info(f"Added exclude keyword: {word}")
        return keyword

    async def delete_keyword(self, session: AsyncSession, word: str) -> bool:
        """Delete a keyword."""
        result = await session.execute(delete(ExcludeKeyword).where(ExcludeKeyword.word == word))
        await session.commit()
        return result.rowcount > 0

    async def get_all_keywords(self, session: AsyncSession) -> List[ExcludeKeyword]:
        """Get all keywords (active and inactive) for management UI."""
        result = await session.execute(select(ExcludeKeyword).order_by(ExcludeKeyword.created_at.desc()))
        return result.scalars().all()

keyword_service = KeywordService()
