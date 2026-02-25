
import asyncio
import sys
import os
# Override for local testing before config import (if possible) OR after import if settings reloads
# But app.core.config usually reads env at import time.
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_HOST"] = "localhost" # Just in case
from datetime import datetime
from sqlalchemy import select

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.db.models import BidAnnouncement, User, UserProfile, UserLicense
from app.db.repositories.bid_repository import BidRepository
from app.core.logging import logger

async def test_hard_match():
    async with AsyncSessionLocal() as session:
        repo = BidRepository(session)
        
        # 1. Setup Test Data
        # User: Seoul, 500M performance, Licenses=["LicenseA", "LicenseB"]
        user_licenses = ["LicenseA", "LicenseB"]
        region_code = "서울"
        perf_amount = 500_000_000.0
        
        # Bid 1: Matches (Seoul, 300M, LicenseA)
        bid1 = BidAnnouncement(
            title="Match Bid",
            content="Content",
            posted_at=datetime.utcnow(),
            url="http://test.com/match",
            region_code="서울",
            min_performance=300_000_000.0,
            license_requirements=["LicenseA"]
        )
        
        # Bid 2: Region Mismatch (Busan)
        bid2 = BidAnnouncement(
            title="Region Fail Bid",
            content="Content",
            posted_at=datetime.utcnow(),
            url="http://test.com/fail_region",
            region_code="부산",
            min_performance=100.0,
            license_requirements=["LicenseA"]
        )
        
        # Bid 3: Performance Fail (600M)
        bid3 = BidAnnouncement(
            title="Perf Fail Bid",
            content="Content",
            posted_at=datetime.utcnow(),
            url="http://test.com/fail_perf",
            region_code="서울",
            min_performance=600_000_000.0,
            license_requirements=["LicenseA"]
        )
        
        # Bid 4: License Fail (LicenseC required)
        bid4 = BidAnnouncement(
            title="License Fail Bid",
            content="Content",
            posted_at=datetime.utcnow(),
            url="http://test.com/fail_lic",
            region_code="서울",
            min_performance=100.0,
            license_requirements=["LicenseC"]
        )

        # Bid 5: National Bid (No region)
        bid5 = BidAnnouncement(
            title="National Bid",
            content="Content",
            posted_at=datetime.utcnow(),
            url="http://test.com/national",
            region_code=None,
            min_performance=100.0,
            license_requirements=["LicenseA"]
        )
        
        session.add_all([bid1, bid2, bid3, bid4, bid5])
        await session.commit()
        
        print("--- Testing Hard Match Logic ---")
        matches = await repo.get_hard_matches(
            region_code=region_code,
            user_performance_amount=perf_amount,
            user_licenses=user_licenses
        )
        
        matched_titles = [b.title for b in matches]
        print(f"User Constraints: Region={region_code}, Perf={perf_amount}, Lic={user_licenses}")
        print(f"Matches Found: {matched_titles}")
        
        expected = ["Match Bid", "National Bid"]
        # Bid 5 should match because Region=None (National) and others pass.
        # But wait, Bid 5 region_code is None. My logic: (Bid.region == region) | (Bid.region == '전국') | (Bid.region is None). So YES.
        
        assert "Match Bid" in matched_titles
        assert "National Bid" in matched_titles
        assert "Region Fail Bid" not in matched_titles
        assert "Perf Fail Bid" not in matched_titles
        assert "License Fail Bid" not in matched_titles
        
        print("✅ Hard Match Verification Passed!")
        
        # Cleanup
        for b in [bid1, bid2, bid3, bid4, bid5]:
            await session.delete(b)
        await session.commit()

from datetime import datetime
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_hard_match())
