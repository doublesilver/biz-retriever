import sys
import os
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

# Mock Env
os.environ["PROJECT_NAME"] = "Test Project"
os.environ["SECRET_KEY"] = "test_secret"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "pass"
os.environ["POSTGRES_DB"] = "db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["OPENAI_API_KEY"] = "sk-test"

from app.db.base import Base
from app.schemas.bid import BidCreate
from app.services.bid_service import bid_service

async def test_service():
    # Use SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestingSessionLocal() as session:
        # 1. Create Bid
        bid_in = BidCreate(
            title="Test Bid",
            content="This is a test bid announcement logic.",
            agency="Test Agency",
            posted_at=datetime.now(),
            url="http://example.com/bid/1"
        )
        new_bid = await bid_service.create_bid(session, bid_in)
        print(f"Created Bid: {new_bid}")
        assert new_bid.id is not None
        assert new_bid.title == "Test Bid"

        # 2. Get Bid
        fetched_bid = await bid_service.get_bid(session, new_bid.id)
        print(f"Fetched Bid: {fetched_bid}")
        assert fetched_bid.title == "Test Bid"

        # 3. Update status
        updated_bid = await bid_service.update_bid_processing_status(session, new_bid.id, True)
        print(f"Updated Bid Processed: {updated_bid.processed}")
        assert updated_bid.processed is True

        print("Service Layer logic verified successfully.")

if __name__ == "__main__":
    asyncio.run(test_service())
