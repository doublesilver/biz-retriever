"""
Synchronous database migration script for Windows compatibility
Fixes asyncpg connection issues by using psycopg2
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.db.base import Base
from app.core.config import settings

def run_migration():
    """Run database migration using synchronous psycopg2"""
    
    # Use psycopg2 (synchronous) instead of asyncpg
    DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    
    print("=" * 60)
    print("🔧 Synchronous Database Migration")
    print("=" * 60)
    print(f"Connecting to: postgresql://{settings.POSTGRES_USER}:***@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    
    try:
        # Create engine with psycopg2
        engine = create_engine(DATABASE_URL, echo=True)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"\n✅ Connected to PostgreSQL: {version}\n")
        
        # Create all tables
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        
        print("\n" + "=" * 60)
        print("✅ All tables created successfully!")
        print("=" * 60)
        
        # Show created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = result.fetchall()
            
            print("\n📋 Created tables:")
            for table in tables:
                print(f"  - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\n💡 Troubleshooting:")
        print("  1. Check if PostgreSQL is running: docker ps")
        print("  2. Verify .env file has correct credentials")
        print("  3. Try: docker-compose restart db")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
