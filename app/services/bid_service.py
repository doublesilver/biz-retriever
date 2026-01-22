from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import BidAnnouncement
from app.schemas.bid import BidCreate, BidUpdate

class BidService:
    async def create_bid(self, session: AsyncSession, bid_in: BidCreate, processed: bool = False) -> BidAnnouncement:
        db_bid = BidAnnouncement(
            title=bid_in.title,
            content=bid_in.content,
            agency=bid_in.agency,
            posted_at=bid_in.posted_at,
            url=str(bid_in.url),
            processed=processed
        )
        session.add(db_bid)
        await session.commit()
        await session.refresh(db_bid)
        return db_bid

    async def get_bid(self, session: AsyncSession, bid_id: int) -> Optional[BidAnnouncement]:
        result = await session.execute(select(BidAnnouncement).where(BidAnnouncement.id == bid_id))
        return result.scalars().first()

    async def get_bids(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        keyword: str = None,
        agency: str = None,
    ) -> List[BidAnnouncement]:
        query = select(BidAnnouncement)
        
        if keyword:
            query = query.where(
                (BidAnnouncement.title.ilike(f"%{keyword}%")) | 
                (BidAnnouncement.content.ilike(f"%{keyword}%"))
            )
        
        if agency:
            query = query.where(BidAnnouncement.agency == agency)

        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    async def update_bid_processing_status(self, session: AsyncSession, bid_id: int, processed: bool) -> Optional[BidAnnouncement]:
        bid = await self.get_bid(session, bid_id)
        if bid:
            bid.processed = processed
            await session.commit()
            await session.refresh(bid)
        return bid

bid_service = BidService()
