
import sys
import os
import asyncio
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock Env
os.environ["PROJECT_NAME"] = "Test Search"
os.environ["SECRET_KEY"] = "test"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "pass"
os.environ["POSTGRES_DB"] = "db"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["OPENAI_API_KEY"] = "sk-test"

# Patch settings & DB
from app.main import app
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
# Import models to register them
from app.db.models import BidAnnouncement, User

# Global Test DB
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

async def test_search():
    # Initialize DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Init Cache Mock (Since we don't want real Redis in Unit Test)
    # We will mock FastAPICache.init in app startup or just bypass strict Redis check
    # For this script, we'll focus on Filtering Logic mainly. 
    # Caching is hard to test with in-memory SQLite + mocked Redis without spinning up real Redis container
    # But we can verify the API accepts params.
    
    # 1. Seed Data
    async with TestingSessionLocal() as session:
        bids = [
            BidAnnouncement(title="AI Project", content="Deep Learning", agency="Agency A", posted_at=datetime.now(), url="http://a.com"),
            BidAnnouncement(title="Construction", content="Building Bridge", agency="Agency B", posted_at=datetime.now(), url="http://b.com"),
            BidAnnouncement(title="Web Dev", content="React Website", agency="Agency A", posted_at=datetime.now(), url="http://c.com"),
        ]
        session.add_all(bids)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        print("Testing Search & Filtering...")

        # 2. Test Keyword Search
        response = await ac.get("/api/v1/bids/?keyword=AI")
        data = response.json()
        print(f"Keyword 'AI' Count: {len(data)}")
        assert len(data) == 1
        assert data[0]["title"] == "AI Project"

        # 3. Test Agency Filter
        response = await ac.get("/api/v1/bids/?agency=Agency A")
        data = response.json()
        print(f"Agency 'Agency A' Count: {len(data)}")
        assert len(data) == 2

        # 4. Test Caching Decorator Presence (Indirect)
        # We can't easily verify hits in a mock script without real Redis hook
        # But successful response means decorator didn't crash app
        print("Caching decorator allowed execution.")
        
        print("Search & Filtering verified successfully.")

from datetime import datetime

if __name__ == "__main__":
    # Mocking FastAPICache to avoid startup error
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    
    asyncio.run(test_search())
