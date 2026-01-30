from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.repositories.base_repository import BaseRepository
from app.db.models import BidAnnouncement
from app.schemas.bid import BidCreate, BidUpdate

class BidRepository(BaseRepository[BidAnnouncement, BidCreate, BidUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(BidAnnouncement, session)

    async def get_by_url(self, url: str) -> Optional[BidAnnouncement]:
        query = select(BidAnnouncement).where(BidAnnouncement.url == url)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_multi_with_filters(
        self,
        skip: int = 0,
        limit: int = 100,
        keyword: Optional[str] = None,
        agency: Optional[str] = None
    ) -> List[BidAnnouncement]:
        query = select(BidAnnouncement)
        
        if keyword:
            query = query.where(
                (BidAnnouncement.title.ilike(f"%{keyword}%")) | 
                (BidAnnouncement.content.ilike(f"%{keyword}%"))
            )
        
        if agency:
            query = query.where(BidAnnouncement.agency.ilike(f"%{agency}%"))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_hard_matches(
        self,
        region_code: Optional[str] = None,
        user_performance_amount: float = 0.0,
        user_licenses: List[str] = [],
        skip: int = 0,
        limit: int = 100
    ) -> List[BidAnnouncement]:
        """
        Hard Match Engine: Zero-Error Filtering
        - Region: Bid must be in user's region OR '전국' OR None
        - Performance: Bid req <= User capacity
        - Licenses: Bid requirements must be subset of User licenses
        """
        query = select(BidAnnouncement)

        # 1. Region Filter
        if region_code:
            query = query.where(
                (BidAnnouncement.region_code == region_code) | 
                (BidAnnouncement.region_code == "전국") |
                (BidAnnouncement.region_code.is_(None))
            )

        # 2. Performance Filter (Bid req <= User cap)
        # 0 or None means no limit
        query = query.where(
            (BidAnnouncement.min_performance <= user_performance_amount) |
            (BidAnnouncement.min_performance.is_(None))
        )
        
        # 3. License Filter (Postgres JSON containment)
        # Bid reqs (A) must be contained in User licenses (B) => A <@ B
        # Standard SQL fallback: We will filter in Python if JSONB is not guaranteed,
        # but for now let's apply SQL filter if possible.
        # Ideally: Bid.license_requirements.contained_by(user_licenses)
        # Using Python filter for safety across DBs (and assuming list size is manageable)
        
        # Optimization: Fetch candidates first, then filter licenses in Python
        # This avoids complex JSON SQL dialect issues for now.
        
        result = await self.session.execute(query.order_by(BidAnnouncement.id.desc()).offset(skip).limit(limit))
        candidates = result.scalars().all()
        
        if not user_licenses:
            # If user has NO licenses, they can only do bids with NO requirements
            return [
                bid for bid in candidates 
                if not bid.license_requirements
            ]
            
        # Filter: Bid reqs must be subset of User licenses
        final_matches = []
        user_license_set = set(user_licenses)
        
        for bid in candidates:
            bid_reqs = bid.license_requirements or []
            # Check subset
            if all(req in user_license_set for req in bid_reqs):
                final_matches.append(bid)
                
        return final_matches

    async def update_processing_status(self, bid_id: int, processed: bool) -> Optional[BidAnnouncement]:
        bid = await self.get(bid_id)
        if bid:
            bid.processed = processed
            await self.session.commit()
            await self.session.refresh(bid)
        return bid
