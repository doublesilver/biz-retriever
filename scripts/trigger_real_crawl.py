import asyncio
from app.services.crawler_service import g2b_crawler
from app.db.session import AsyncSessionLocal
from app.db.models import BidAnnouncement
from app.core.logging import logger

async def trigger_and_save():
    print("🚀 G2B 크롤링 및 DB 저장 시작...")
    try:
        announcements = await g2b_crawler.fetch_new_announcements()
        print(f"✅ {len(announcements)}건 수집 완료 (필터링 통과)")
        
        async with AsyncSessionLocal() as session:
            for data in announcements:
                # 중복 체크
                from sqlalchemy import select
                stmt = select(BidAnnouncement).where(BidAnnouncement.url == data['url'])
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    continue
                
                # 중요도 계산
                data["importance_score"] = g2b_crawler.calculate_importance_score(data)
                
                # 저장
                new_announcement = BidAnnouncement(**data)
                session.add(new_announcement)
                await session.commit()
                print(f"💾 저장 성공: {data['title']} (첨부파일: {'O' if data.get('attachment_content') else 'X'})")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        logger.error(f"Trigger Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(trigger_and_save())
