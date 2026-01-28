import asyncio
from asgiref.sync import async_to_sync
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.worker.celery_app import celery_app
from app.services.bid_service import bid_service
from app.services.rag_service import rag_service
from app.services.crawler_service import g2b_crawler
from app.services.notification_service import slack_notification
from app.db.models import BidAnnouncement
from app.core.logging import logger
from app.core.config import settings

# Helper function to get a fresh SYNC session for Celery tasks
def get_task_session_maker():
    # Use synchronous postgresql driver
    sync_db_url = settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+asyncpg", "postgresql")
    
    engine = create_engine(
        sync_db_url,
        echo=False,
        pool_pre_ping=True,
    )
    return engine, sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )

@celery_app.task(name="app.worker.tasks.process_bid_analysis")
def process_bid_analysis(bid_id: int):
    """
    Celery task to analyze a bid (Synchronous DB, Async Service calls)
    """
    engine, SessionLocal = get_task_session_maker()
    try:
        with SessionLocal() as session:
            # 1. Fetch Bid (Sync)
            bid = session.get(BidAnnouncement, bid_id)
            if not bid:
                logger.warning(f"Bid {bid_id} 찾을 수 없음")
                return

            # 2. Analyze (Async Service Call)
            if not bid.processed:
                # Run async RAG service synchronously
                analysis_result = async_to_sync(rag_service.analyze_bid)(bid.content)
                logger.info(f"Bid {bid_id} 분석 완료: {analysis_result}")

                # 3. Update Status and Save Result (Sync)
                bid.ai_summary = analysis_result.get("summary")
                bid.ai_keywords = analysis_result.get("keywords")
                bid.processed = True
                
                session.add(bid)
                session.commit()
                
                logger.info(f"Bid {bid_id} 처리 및 저장 완료")

                # Broadcast Analysis Completion (Async)
                try:
                    from app.core.websocket import manager
                    import json
                    message = json.dumps({
                        "type": "analysis_completed",
                        "bid_id": bid_id,
                        "title": bid.title,
                        "summary": bid.ai_summary
                    })
                    # Fire and forget for websocket broadcast in sync context
                    # Or use async_to_sync if strictly needed, but might be overkill for broadcast
                    async_to_sync(manager.broadcast)(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast analysis: {e}")
    finally:
        engine.dispose()


@celery_app.task(name="app.worker.tasks.crawl_g2b_bids")
def crawl_g2b_bids():
    """
    G2B 공고 크롤링 태스크
    """
    engine, SessionLocal = get_task_session_maker()
    try:
        with SessionLocal() as session:
            # 1. 수집 제외 키워드 목록 조회 (Sync)
            from app.db.models import ExcludeKeyword
            stmt = select(ExcludeKeyword.word).where(ExcludeKeyword.is_active == True)
            dynamic_excludes = session.execute(stmt).scalars().all()
            exclude_keywords = list(set(g2b_crawler.DEFAULT_EXCLUDE_KEYWORDS + list(dynamic_excludes)))
            
            # 2. 크롤링 실행 (Async Service Call)
            # Pass keywords to avoid internal DB access in crawler_service
            announcements = async_to_sync(g2b_crawler.fetch_new_announcements)(exclude_keywords=exclude_keywords)
            logger.info(f"G2B 크롤링 완료: {len(announcements)}건")
            
            if not announcements:
                return
            
            # 2. DB 저장 및 알림 (Sync DB)
            for announcement_data in announcements:
                # 중복 체크 (URL 기준)
                stmt = select(BidAnnouncement).where(BidAnnouncement.url == announcement_data["url"])
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    continue
                
                # 중요도 계산 (Sync function)
                importance_score = g2b_crawler.calculate_importance_score(announcement_data)
                announcement_data["importance_score"] = importance_score
                
                # DB 저장
                new_announcement = BidAnnouncement(**announcement_data)
                session.add(new_announcement)
                session.commit()
                session.refresh(new_announcement) # ID 확보

                # Phase 3: Constraint Extraction & Hard Match Prep
                # 중요도가 일정 수준 이상이거나, 모든 공고에 대해 수행?
                # 비용 문제로 인해 Importance Score >= 1 인 경우만 수행하거나,
                # 일단 모든 "유효 공고"(필터링 통과)에 대해 수행.
                try:
                    from app.services.constraint_service import constraint_service
                    constraints = async_to_sync(constraint_service.extract_constraints)(new_announcement)
                    
                    if constraints:
                        # Update fields
                        new_announcement.region_code = constraints.get("region_code")
                        new_announcement.min_performance = constraints.get("min_performance")
                        new_announcement.license_requirements = constraints.get("license_requirements")
                        
                        session.add(new_announcement)
                        session.commit()
                        logger.info(f"제약 조건 추출 완료 Bid {new_announcement.id}: {constraints}")
                except Exception as e:
                    logger.error(f"제약 조건 추출 중 오류 Bid {new_announcement.id}: {e}")
                
                # 중요 공고(2점 이상)는 즉시 AI 분석 요청
                if importance_score >= 2:
                    process_bid_analysis.delay(new_announcement.id)
                    logger.info(f"AI 분석 요청: {new_announcement.id}")
                
                # Slack 알림 (Async Service Call)
                if importance_score >= 2 and not new_announcement.is_notified:
                    success = async_to_sync(slack_notification.send_bid_notification)(new_announcement)
                    if success:
                        new_announcement.is_notified = True
                        session.commit()
                
                logger.info(f"새 공고 저장: {new_announcement.title} (중요도: {importance_score})")

                # Broadcast New Bid
                try:
                    from app.core.websocket import manager
                    import json
                    message = json.dumps({
                        "type": "new_bid",
                        "bid_id": new_announcement.id,
                        "title": new_announcement.title,
                        "agency": new_announcement.agency
                    })
                    async_to_sync(manager.broadcast)(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast new bid: {e}")
    finally:
        engine.dispose()


@celery_app.task(name="app.worker.tasks.send_morning_digest")
def send_morning_digest():
    """
    모닝 브리핑 전송
    """
    engine, SessionLocal = get_task_session_maker()
    try:
        with SessionLocal() as session:
            # 밤사이(지난 12시간) 수집된 공고 조회
            from datetime import datetime, timedelta
            since = datetime.utcnow() - timedelta(hours=12)
            
            stmt = select(BidAnnouncement)\
                .where(BidAnnouncement.crawled_at >= since)\
                .order_by(BidAnnouncement.importance_score.desc())
            
            result = session.execute(stmt)
            announcements = result.scalars().all()
            
            if announcements:
                async_to_sync(slack_notification.send_digest)(announcements)
                logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
    finally:
        engine.dispose()