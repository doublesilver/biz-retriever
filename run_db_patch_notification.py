import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def add_notification_columns():
    print(f"Connecting to {settings.DATABASE_URL}...")
    DATABASE_URL = "postgresql+asyncpg://admin:changeme@db:5432/biz_retriever"
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("1. Adding 'slack_webhook_url' column to user_profiles...")
        try:
            await conn.execute(text("ALTER TABLE user_profiles ADD COLUMN slack_webhook_url VARCHAR"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")

        print("2. Adding 'is_email_enabled' column to user_profiles...")
        try:
            await conn.execute(text("ALTER TABLE user_profiles ADD COLUMN is_email_enabled BOOLEAN DEFAULT FALSE"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")

        print("3. Adding 'is_slack_enabled' column to user_profiles...")
        try:
            await conn.execute(text("ALTER TABLE user_profiles ADD COLUMN is_slack_enabled BOOLEAN DEFAULT FALSE"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_notification_columns())
