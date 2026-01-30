import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def add_columns():
    # Use the internal docker URL if running inside container, but settings.DATABASE_URL should be correct if env is correct.
    # We are running inside container, so settings loading .env inside container should work.
    
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("1. Adding 'provider' column...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN provider VARCHAR DEFAULT 'email'"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")

        print("2. Adding 'provider_id' column...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN provider_id VARCHAR"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")

        print("3. Adding 'profile_image' column...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN profile_image VARCHAR"))
            print("   -> Success")
        except Exception as e:
            print(f"   -> Failed (might exist): {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_columns())
