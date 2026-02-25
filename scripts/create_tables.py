"""
Synchronous migration script for Windows compatibility
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from app.db.base import Base
from app.core.config import settings

# Use psycopg2 instead of asyncpg for migrations
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

print(f"Connecting to: postgresql://{settings.POSTGRES_USER}:***@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

engine = create_engine(DATABASE_URL)

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("✅ All tables created successfully!")
