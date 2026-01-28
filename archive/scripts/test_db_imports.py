
import sys
import os
import asyncio
from unittest.mock import patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables BEFORE importing config
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

# Now import app modules
from app.db.base import Base
from app.db.models import BidAnnouncement
from sqlalchemy.orm import DeclarativeBase

async def test_imports():
    print("Successfully imported Base and BidAnnouncement.")
    print(f"Table name: {BidAnnouncement.__tablename__}")
    
    # Verify metadata
    assert "bid_announcements" in Base.metadata.tables
    print("Metadata check passed.")

if __name__ == "__main__":
    asyncio.run(test_imports())
