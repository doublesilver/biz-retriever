import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
import socket

async def test_connection():
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"Postgres Server: {settings.POSTGRES_SERVER}")
    
    # DNS Check
    try:
        addr_info = socket.getaddrinfo(settings.POSTGRES_SERVER, settings.POSTGRES_PORT)
        print(f"DNS Resolution ({settings.POSTGRES_SERVER}): {addr_info}")
    except Exception as e:
        print(f"DNS Resolution Failed: {e}")

    # SQLAlchemy Connect Check
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            print("Successfully connected to Database!")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
