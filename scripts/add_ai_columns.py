from sqlalchemy import create_engine, text
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

def add_columns():
    print("🔌 Connecting to Database...")
    # Force sync driver for this script
    db_url = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("🛠️ Adding 'ai_summary' column...")
        try:
            conn.execute(text("ALTER TABLE bid_announcements ADD COLUMN IF NOT EXISTS ai_summary TEXT"))
            print("✅ ai_summary added (or already exists).")
        except Exception as e:
            print(f"❌ Failed to add ai_summary: {e}")

        print("🛠️ Adding 'ai_keywords' column...")
        try:
            conn.execute(text("ALTER TABLE bid_announcements ADD COLUMN IF NOT EXISTS ai_keywords JSON DEFAULT '[]'"))
            print("✅ ai_keywords added (or already exists).")
        except Exception as e:
            print(f"❌ Failed to add ai_keywords: {e}")
            
        conn.commit()

if __name__ == "__main__":
    add_columns()
