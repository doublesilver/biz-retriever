import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def connect():
    dsn = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    print(f"Connecting to: {dsn}")
    try:
        conn = await asyncpg.connect(dsn)
        print("Success!")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(connect())
