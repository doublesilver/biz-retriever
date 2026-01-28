import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.logging import logger

async def migrate_db():
    async with AsyncSessionLocal() as session:
        try:
            logger.info("Starting manual migration for Phase 3...")
            
            # 1. region_code 추가
            try:
                await session.execute(text("ALTER TABLE bid_announcements ADD COLUMN region_code VARCHAR"))
                await session.execute(text("CREATE INDEX ix_bid_announcements_region_code ON bid_announcements (region_code)"))
                logger.info("Added region_code column")
            except Exception as e:
                logger.warning(f"region_code column might already exist: {e}")
                await session.rollback()

            # 2. min_performance 추가
            try:
                await session.execute(text("ALTER TABLE bid_announcements ADD COLUMN min_performance FLOAT DEFAULT 0.0"))
                logger.info("Added min_performance column")
            except Exception as e:
                logger.warning(f"min_performance column might already exist: {e}")
                await session.rollback()

            # 3. license_requirements 추가
            try:
                # JSON type for Postgres
                await session.execute(text("ALTER TABLE bid_announcements ADD COLUMN license_requirements JSON DEFAULT '[]'"))
                logger.info("Added license_requirements column")
            except Exception as e:
                logger.warning(f"license_requirements column might already exist: {e}")
                await session.rollback()

            await session.commit()
            logger.info("Migration completed successfully.")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate_db())
