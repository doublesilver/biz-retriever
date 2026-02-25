import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT count(*) FROM bid_announcements'))
        print(f"실제 DB 공고 수: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(check())
