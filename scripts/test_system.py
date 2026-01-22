
import sys
import os
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock Env
os.environ["PROJECT_NAME"] = "Test System"
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
from app.core.config import settings
from app.main import app
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

# Global Test DB
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

async def test_system():
    # Initialize DB
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock Celery Task
    with patch("app.worker.tasks.process_bid_analysis.delay") as mock_task:
        # Mock File Service to avoid real PDF parsing issues in test env
        with patch("app.services.file_service.file_service.get_text_from_file", return_value="Parsed PDF Content") as mock_parse:
            
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                print("Testing End-to-End Pipeline...")

                # 0. Authentication (Register & Login)
                print("Step 0: Authenticating...")
                # Register
                auth_payload = {"email": "system_test@example.com", "password": "password123"}
                await ac.post("/api/v1/auth/register", json=auth_payload)
                
                # Login
                form_data = {"username": "system_test@example.com", "password": "password123"}
                login_res = await ac.post("/api/v1/auth/login/access-token", data=form_data)
                assert login_res.status_code == 200, f"Login failed: {login_res.text}"
                token = login_res.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                # 1. Upload File
                files = {'file': ('test.pdf', b'%PDF-1.4 mock content', 'application/pdf')}
                response = await ac.post("/api/v1/bids/upload", files=files, headers=headers)
                
                print(f"Upload Status: {response.status_code}")
                if response.status_code != 201:
                    print(response.text)
                assert response.status_code == 201
                
                data = response.json()
                print(f"Created Bid ID: {data['id']}")
                assert data['content'] == "Parsed PDF Content"
                
                # Verify Celery Task Triggered
                mock_task.assert_called_once_with(data['id'])
                print("Celery Task Triggered: Yes")

                print("System verified successfully.")

if __name__ == "__main__":
    asyncio.run(test_system())
