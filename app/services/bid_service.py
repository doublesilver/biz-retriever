from typing import List, Optional

from app.core.logging import logger
from app.db.models import BidAnnouncement
from app.db.repositories.bid_repository import BidRepository
from app.schemas.bid import BidCreate, BidUpdate
from app.services.match_service import hard_match_engine
from app.services.subscription_service import subscription_service


class BidService:
    async def create_bid(
        self, repo: BidRepository, bid_in: BidCreate, processed: bool = False
    ) -> BidAnnouncement:
        # Pydantic model itself doesn't have 'processed', so we might handle it separately
        # or update the schema. For now, we create standard, then update if needed.
        # Actually BidCreate doesn't have processed.
        # Let's override or handle it.
        # BaseRepo create expects BidCreate, but we want to set processed=True/False
        # We can just create with repo, then update? Or repo.create handles it if we pass dict?
        # BaseRepo create uses obj_in.model_dump().

        # Let's adjust: BidCreate usually comes from API.
        # If we need internal creation with extra fields, we might need a richer repo method or
        # create the object manually.

        # For simplicity in this phase:
        db_bid = await repo.create(bid_in)
        if processed:
            # We can add a custom update in repo or just attribute set if attached
            # But repo.create commits and refreshes.
            db_bid.processed = processed
            await repo.session.commit()
            await repo.session.refresh(db_bid)
        return db_bid

    async def get_bid(
        self, repo: BidRepository, bid_id: int
    ) -> Optional[BidAnnouncement]:
        return await repo.get(bid_id)

    async def get_bids(
        self,
        repo: BidRepository,
        skip: int = 0,
        limit: int = 100,
        keyword: Optional[str] = None,
        agency: Optional[str] = None,
    ) -> List[BidAnnouncement]:
        return await repo.get_multi_with_filters(
            skip=skip, limit=limit, keyword=keyword, agency=agency
        )

    async def update_bid_processing_status(
        self, repo: BidRepository, bid_id: int, processed: bool
    ) -> Optional[BidAnnouncement]:
        return await repo.update_processing_status(bid_id, processed)

    async def update_bid(
        self, repo: BidRepository, db_bid: BidAnnouncement, bid_in: BidUpdate
    ) -> BidAnnouncement:
        return await repo.update(db_bid, bid_in)

    async def get_matching_bids(
        self, repo: BidRepository, profile, user=None, skip: int = 0, limit: int = 100
    ) -> List[BidAnnouncement]:
        """
        Execute Hard Match Logic with Zero False Positives

        Uses HardMatchEngine for precise 3-stage validation:
        1. Region matching
        2. License verification
        3. Performance capacity check
        """
        # 0. Check Plan Limits
        max_allowed = 100  # Default
        if user:
            plan = await subscription_service.get_user_plan(user)
            limits = await subscription_service.get_plan_limits(plan)
            max_allowed = limits["hard_match_limit"]

            # Restrict limit
            if limit > max_allowed:
                limit = max_allowed

            # If skip is beyond max_allowed, return empty (e.g. they can't paginate past 3)
            if skip >= max_allowed:
                return []

        # 1. Get all recent bids (last 30 days)
        all_bids = await repo.get_multi_with_filters(skip=0, limit=1000)

        # 2. Apply Hard Match filter using engine
        matched_bids = []
        for bid in all_bids:
            is_match, reasons, details = hard_match_engine.evaluate(bid, profile)
            if is_match:
                matched_bids.append(bid)
                logger.info(f"Hard Match: bid_id={bid.id}, title={bid.title[:30]}")

        # 3. Apply pagination
        total_matched = len(matched_bids)
        paginated = matched_bids[skip : skip + limit]

        logger.info(
            f"Hard Match Results: {len(paginated)}/{total_matched} bids matched (skip={skip}, limit={limit})"
        )

        return paginated


bid_service = BidService()
