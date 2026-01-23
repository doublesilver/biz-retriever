import asyncio
from asgiref.sync import async_to_sync
from app.worker.celery_app import celery_app
from app.services.bid_service import bid_service
from app.services.rag_service import rag_service
from app.services.crawler_service import g2b_crawler
from app.services.notification_service import slack_notification
from app.db.session import AsyncSessionLocal
from app.db.models import BidAnnouncement
from app.core.logging import logger
from sqlalchemy import select

@celery_app.task(name="app.worker.tasks.process_bid_analysis")
def process_bid_analysis(bid_id: int):
    """
    Celery task to analyze a bid asynchronously.
    """
    async def _process():
        async with AsyncSessionLocal() as session:
            # 1. Fetch Bid
            bid = await bid_service.get_bid(session, bid_id)
            if not bid:
                logger.warning(f"Bid {bid_id} 찾을 수 없음")
                return

            # 2. Analyze (Mock RAG for now if no key)
            if not bid.processed:
                analysis_result = await rag_service.analyze_bid(bid.content)
                logger.info(f"Bid {bid_id} 분석 완료: {analysis_result}")

                # 3. Update Status
                await bid_service.update_bid_processing_status(session, bid_id, True)
                logger.info(f"Bid {bid_id} 처리 완료로 표시")

    # Run async function in sync Celery worker
    async_to_sync(_process)()


@celery_app.task(name="app.worker.tasks.crawl_g2b_bids")
def crawl_g2b_bids():
    """
    G2B 공고 크롤링 태스크
    스케줄: 하루 3회 (08:00, 12:00, 18:00)
    """
    async def _crawl():
        async with AsyncSessionLocal() as session:
            # 1. 크롤링 실행
            announcements = await g2b_crawler.fetch_new_announcements()
            logger.info(f"G2B 크롤링 완료: {len(announcements)}건")
            
            if not announcements:
                return
            
            # 2. DB 저장 및 알림
            for announcement_data in announcements:
                # 중복 체크 (URL 기준)
                existing = await session.execute(
                    select(BidAnnouncement).where(
                        BidAnnouncement.url == announcement_data["url"]
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                # 중요도 계산
                importance_score = g2b_crawler.calculate_importance_score(announcement_data)
                announcement_data["importance_score"] = importance_score
                
                # DB 저장
                new_announcement = BidAnnouncement(**announcement_data)
                session.add(new_announcement)
                await session.commit()
                await session.refresh(new_announcement)
                
                # Slack 알림 (중요도 2 이상만)
                if importance_score >= 2 and not new_announcement.is_notified:
                    success = await slack_notification.send_bid_notification(new_announcement)
                    if success:
                        new_announcement.is_notified = True
                        await session.commit()
                
                logger.info(f"새 공고 저장: {new_announcement.title} (중요도: {importance_score})")
    
    async_to_sync(_crawl)()


@celery_app.task(name="app.worker.tasks.send_morning_digest")
def send_morning_digest():
    """
    모닝 브리핑 전송
    스케줄: 매일 08:30
    """
    async def _send():
        async with AsyncSessionLocal() as session:
            # 밤사이(지난 12시간) 수집된 공고 조회
            from datetime import datetime, timedelta
            since = datetime.utcnow() - timedelta(hours=12)
            
            result = await session.execute(
                select(BidAnnouncement)
                .where(BidAnnouncement.crawled_at >= since)
                .order_by(BidAnnouncement.importance_score.desc())
            )
            announcements = result.scalars().all()
            
            if announcements:
                await slack_notification.send_digest(announcements)
                logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
    
    async_to_sync(_send)()
