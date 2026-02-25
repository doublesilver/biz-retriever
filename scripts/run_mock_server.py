import asyncio
import sys
import os
sys.path.append(os.getcwd()) # Add current directory to path so 'app' module can be found
import uvicorn
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.api import deps
from app.db import session as db_session_module
from app.core.security import get_password_hash
from app.db.models import User, BidAnnouncement, BidResult

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_server")

# In-memory SQLite DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db():
    async with SessionLocal() as session:
        yield session

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        # Create User
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("password123"), # password123
            is_active=True,
            is_superuser=True
        )
        db.add(user)
        
        # Create Sample Bids
        bids = [
            BidAnnouncement(
                title="[AI 예측] 서울대학교병원 구내식당 위탁운영",
                content="상세 내용...",
                agency="서울대학교병원",
                url="https://example.com/1",
                source="G2B",
                estimated_price=500000000,
                status="new",
                importance_score=3,
                posted_at=datetime.utcnow(),
                deadline=None,
                processed=True
            ),
             BidAnnouncement(
                title="[AI 예측] 강남구청 카페 테리아 임대",
                content="상세 내용...",
                agency="강남구청",
                url="https://example.com/2",
                source="Onbid",
                estimated_price=100000000,
                status="bidding",
                importance_score=2,
                posted_at=datetime.utcnow(),
                deadline=None,
                processed=True
            )
        ]
        db.add_all(bids)
        await db.commit()
        
        # Create Sample Bid Results (for ML) - Need at least 10 for training
        bid_results = [
            BidResult(
                bid_number=f"2025010{i}-00{i}",
                title=f"과거 데이터: 2024년 식당 운영 #{i}",
                winning_price=int(500000000 * (0.92 + i * 0.01)),  # 92-102% range
                estimated_price=500000000,
                winning_company=f"업체{i}",
                source="G2B"
            ) for i in range(1, 12)  # 11 records
        ]
        db.add_all(bid_results)
        await db.commit()
        logger.info(f"✅ Seeded Mock Data: User(test@example.com), 2 Bids, {len(bid_results)} BidResults")

# Apply overrides
app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[db_session_module.get_db] = override_get_db
app.router.on_startup.clear()

# Mock Crawler Endpoint
@app.post("/api/v1/crawler/trigger")
async def mock_crawler_trigger():
    logger.info("🕷️ Mock Crawler Triggered!")
    await asyncio.sleep(2) # Simulate work
    
    # Add a new mock bid
    async with SessionLocal() as db:
        new_bid = BidAnnouncement(
            title=f"[크롤링] 새로 발견된 입찰 공고 {int(datetime.now().timestamp())}",
            content="이것은 모의 크롤링을 통해 수집된 공고입니다.",
            agency="새로운 공공기관",
            url="https://g2b.go.kr/mock",
            source="G2B",
            estimated_price=88000000,
            status="new",
            importance_score=1,
            posted_at=datetime.utcnow(),
            deadline=None,
            processed=False
        )
        db.add(new_bid)
        await db.commit()
    
    return {"status": "success", "message": "Mock crawling completed. 1 new bid found."}

from app.services.ml_service import ml_service

# Patch Startup Event to seed data & init cache & train ML
@app.on_event("startup")
async def on_startup():
    FastAPICache.init(InMemoryBackend(), prefix="mock-cache")
    logger.info("✅ InMemory Cache Initialized")
    
    await seed_data()
    
    # Train ML with seeded data
    async with SessionLocal() as db:
        logger.info("🧠 Training Mock ML Model...")
        result = await ml_service.train_model(db)
        logger.info(f"✅ Mock ML Training Result: {result}")

if __name__ == "__main__":
    import sys
    # Fix for Windows asyncio
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    logger.info("🚀 Starting Mock Server on http://localhost:8004")
    logger.info("🔑 Test Account: test@example.com / password123")
    
    # Run Uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
