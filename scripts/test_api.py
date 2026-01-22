
import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime

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

# Patch settings to use SQLite for tests
from app.core.config import settings
settings.POSTGRES_SERVER = "sqlite"

from app.main import app
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

# Override DB Dependency
# Global Test DB
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

async def test_api():
    # Initialize DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Health Check
            response = await ac.get("/health")
            print(f"Health Check: {response.json()}")
            assert response.status_code == 200

            # 1.5 Authentication (Register & Login)
            # Register
            auth_payload = {"email": "api_test@example.com", "password": "password123"}
            await ac.post("/api/v1/auth/register", json=auth_payload)
            
            # Login
            form_data = {"username": "api_test@example.com", "password": "password123"}
            login_res = await ac.post("/api/v1/auth/login/access-token", data=form_data)
            assert login_res.status_code == 200, f"Login failed: {login_res.text}"
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Create Bid
            payload = {
                "title": "API Test Bid",
                "content": "Content for API Test",
                "agency": "API Agency",
                "posted_at": datetime.now().isoformat(),
                "url": "http://api.test/1"
            }
            response = await ac.post("/api/v1/bids/", json=payload, headers=headers)
            print(f"Create Bid: {response.status_code}")
            if response.status_code != 201:
                print(f"Error Response: {response.text}")
            assert response.status_code == 201
            data = response.json()
            bid_id = data["id"]
            assert data["title"] == "API Test Bid"

            # 3. Get Bid
            response = await ac.get(f"/api/v1/bids/{bid_id}")
            print(f"Get Bid: {response.status_code}")
            assert response.status_code == 200
            assert response.json()["title"] == "API Test Bid"

            print("API Layer verified successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    asyncio.run(test_api())
