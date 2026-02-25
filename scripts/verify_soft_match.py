import sys
import os
import asyncio

# Create a valid event loop for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# [FIX] Add project root to sys.path to allow 'app' import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, BidAnnouncement, UserProfile
from app.services.matching_service import matching_service

async def main():
    async with AsyncSessionLocal() as db:
        # 1. Get User
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        user = result.scalar_one_or_none()
        if not user:
            print("User admin@example.com not found. Trying ID 1.")
            result = await db.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
        
        # [FIX] Handle missing profile
        profile = None
        if user and user.profile:
            profile = user.profile
        else:
            print("User or Profile not found in DB. Using Mock Profile for Testing.")
            # Create Mock Profile in memory
            profile = UserProfile(
                user_id=user.id if user else 999,
                keywords=["자전거", "보험", "지하수", "폐기물"],
                location_code="00"
            )

        print(f"User Email: {user.email if user else 'Mock User'}")
        print(f"Keywords: {profile.keywords}")
        print(f"Location: {profile.location_code}")

        # 2. Get a Bid (Recent one)
        result = await db.execute(select(BidAnnouncement).order_by(BidAnnouncement.id.desc()).limit(1))
        bid = result.scalar_one_or_none()
        
        if not bid:
            print("No bids found.")
            return

        print(f"\nBid: {bid.title}")
        print(f"Region: {bid.region_code}")
        print(f"Importance: {bid.importance_score}")

        # 3. Calculate Soft Match
        soft_result = matching_service.calculate_soft_match(profile, bid)
        print(f"\n[Soft Match Result]")
        print(f"Score: {soft_result['score']}")
        print(f"Breakdown: {soft_result['breakdown']}")

        # 4. Check Hard Match
        hard_result = matching_service.check_hard_match(profile, bid)
        print(f"\n[Hard Match Result]")
        print(f"Is Match: {hard_result['is_match']}")
        print(f"Reasons: {hard_result['reasons']}")

if __name__ == "__main__":
    asyncio.run(main())
