
import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock Env
os.environ["PROJECT_NAME"] = "Test Auth"
os.environ["SECRET_KEY"] = "test_key_for_jwt"
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
from app.core import security

# Global Test DB
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

async def test_auth():
    # Initialize DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        print("Testing Authentication System...")

        # 1. Register User
        payload = {"email": "test@example.com", "password": "password123"}
        response = await ac.post("/api/v1/auth/register", json=payload)
        print(f"Register: {response.status_code}")
        if response.status_code != 200:
            print(response.text)
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

        # 2. Login (Get Token) - Form Data
        form_data = {"username": "test@example.com", "password": "password123"}
        response = await ac.post("/api/v1/auth/login/access-token", data=form_data)
        print(f"Login: {response.status_code}")
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        
        # 3. Access Protected Route (Create Bid)
        headers = {"Authorization": f"Bearer {token}"}
        bid_payload = {
            "title": "Authenticated Bid",
            "content": "Secret Content",
            "agency": "Secret Agency",
            "posted_at": datetime.now().isoformat(),
            "url": "http://secure.bid"
        }
        response = await ac.post("/api/v1/bids/", json=bid_payload, headers=headers)
        print(f"Protected Bid Create: {response.status_code}")
        assert response.status_code == 201
        
        # 4. Access Protected Route without Token (Should Fail)
        response = await ac.post("/api/v1/bids/", json=bid_payload)
        print(f"Unprotected Access: {response.status_code}")
        assert response.status_code == 401

        print("Authentication verified successfully.")

if __name__ == "__main__":
    asyncio.run(test_auth())
