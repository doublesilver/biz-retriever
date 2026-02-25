import asyncio
import sys
import os

# Add the project root to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db.session import engine
from app.db.models import BidAnnouncement, User, UserProfile, UserLicense, UserPerformance, BidResult, CrawlerLog, ExcludeKeyword
from app.core.logging import logger

async def recreate_db():
    logger.info("Dropping all tables...")
    async with engine.begin() as conn:
        # Drop all tables managed by Base
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ All tables dropped.")
        
        # Recreate all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ All tables recreated with latest schema.")

if __name__ == "__main__":
    try:
        asyncio.run(recreate_db())
        print("Success: Database schema has been reset.")
    except Exception as e:
        print(f"Error recreating database: {e}")
        sys.exit(1)
