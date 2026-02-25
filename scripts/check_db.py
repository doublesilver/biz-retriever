import asyncio
import asyncpg
import sys
from app.core.config import settings

async def check_db():
    print(f"Connecting to {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT} as {settings.POSTGRES_USER}...")
    try:
        conn = await asyncpg.connect(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT
        )
        print("Success! Connected to Database.")
        await conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
