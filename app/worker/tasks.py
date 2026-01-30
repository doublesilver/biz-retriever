import asyncio
from asgiref.sync import async_to_sync
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.worker.celery_app import celery_app
from app.services.bid_service import bid_service
from app.services.rag_service import rag_service
from app.api.deps import get_crawler_service
from app.services.notification_service import NotificationService
from app.db.models import BidAnnouncement, User, UserProfile
from app.core.logging import logger
from app.core.config import settings

def get_task_session_maker():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI.replace("postgresql+asyncpg", "postgresql"))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

@celery_app.task(name="app.worker.tasks.crawl_g2b_bids")
def crawl_g2b_bids():
    engine, SessionLocal = get_task_session_maker()
    
    # Initialize Service via DI
    g2b_crawler = get_crawler_service()
    try:
        with SessionLocal() as session:
            # 1. 수집 제외 키워드 및 포함 키워드(Dynamic) 조회 (Sync)
            from app.db.models import ExcludeKeyword, UserKeyword
            
            # Excludes
            stmt_exclude = select(ExcludeKeyword.word).where(ExcludeKeyword.is_active == True)
            dynamic_excludes = session.execute(stmt_exclude).scalars().all()
            exclude_keywords = list(set(g2b_crawler.DEFAULT_EXCLUDE_KEYWORDS + list(dynamic_excludes)))
            
            # Includes (Dynamic from UserKeyword)
            stmt_include = select(UserKeyword.keyword).where(
                UserKeyword.is_active == True, 
                UserKeyword.category == 'include'
            ).distinct()
            dynamic_includes = session.execute(stmt_include).scalars().all()
            include_keywords = list(dynamic_includes)
            
            # Fallback if DB is empty (Migration phase)
            if not include_keywords:
                include_keywords = g2b_crawler.INCLUDE_KEYWORDS_CONCESSION + g2b_crawler.INCLUDE_KEYWORDS_FLOWER
            
            # 2. 크롤링 실행 (Async Service Call)
            announcements = async_to_sync(g2b_crawler.fetch_new_announcements)(
                exclude_keywords=exclude_keywords,
                include_keywords=include_keywords
            )
            logger.info(f"G2B 크롤링 완료: {len(announcements)}건")
            
            if not announcements:
                return
            
            # Pre-fetch all active users with profiles and keywords for notification (Optimized)
            from sqlalchemy.orm import selectinload
            stmt = select(User).where(User.is_active == True).options(
                selectinload(User.full_profile),
                selectinload(User.keywords)
            )
            active_users = session.execute(stmt).scalars().all()
            
            # 2. DB 저장 및 알림 (Sync DB)
            for announcement_data in announcements:
                stmt = select(BidAnnouncement).where(BidAnnouncement.url == announcement_data["url"])
                existing = session.execute(stmt).scalar_one_or_none()
                
                if existing:
                    continue
                
                importance_score = g2b_crawler.calculate_importance_score(announcement_data)
                announcement_data["importance_score"] = importance_score
                
                # DB 저장
                new_announcement = BidAnnouncement(**announcement_data)
                session.add(new_announcement)
                session.commit()
                session.refresh(new_announcement)

                # AI Analysis Request
                if importance_score >= 2:
                    process_bid_analysis.delay(new_announcement.id)

                # ---------------------------------------------------------
                # Phase 8: Per-User Keyword Notification
                # ---------------------------------------------------------
                for user in active_users:
                    # Phase 3: Use UserKeyword table
                    if not user.keywords:
                        continue
                        
                    # Filter active include keywords
                    user_keywords = [
                        k.keyword for k in user.keywords 
                        if k.is_active and k.category == 'include'
                    ]
                    
                    if not user_keywords:
                        continue
                        
                    # Check Match
                    title = new_announcement.title
                    content = new_announcement.content or ""
                    full_text = f"{title} {content}"
                    
                    matched = [k for k in user_keywords if k in full_text]
                    
                    if matched:
                        # Send Notification (Async to Sync)
                        async_to_sync(NotificationService.notify_bid_match)(user, new_announcement, matched)
                        logger.info(f"알림 발송: User {user.id} -> Bid {new_announcement.id} (키워드: {matched})")

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
                # async_to_sync(slack_notification.send_digest)(announcements)
                logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
    finally:
        engine.dispose()

@celery_app.task(name="app.worker.tasks.process_bid_analysis")
def process_bid_analysis(bid_id: int):
    """
    공고 분석 및 키워드 추출 (AI)
    """
    engine, SessionLocal = get_task_session_maker()
    try:
        with SessionLocal() as session:
            # 1. 공고 조회
            stmt = select(BidAnnouncement).where(BidAnnouncement.id == bid_id)
            bid = session.execute(stmt).scalar_one_or_none()
            
            if not bid:
                logger.error(f"분석 대상 공고 없음: {bid_id}")
                return

            # 2. AI 분석 (RAG Service)
            # Combine Title + Content
            full_text = f"{bid.title} {bid.content}"
            # if bid.attachment_content:
            #     full_text += f" [첨부파일 내용] {bid.attachment_content[:2000]}"
            
            analysis_result = async_to_sync(rag_service.analyze_bid)(full_text)
            
            # 3. 결과 저장
            bid.ai_summary = analysis_result.get("summary")
            bid.ai_keywords = analysis_result.get("keywords")
            
            # Phase 3: Hard Match Fields
            bid.region_code = analysis_result.get("region_code")
            bid.license_requirements = analysis_result.get("license_requirements")
            bid.min_performance = analysis_result.get("min_performance")
            
            bid.processed = True
            
            session.commit()
            logger.info(f"AI 분석 완료: {bid.title}")
            
    finally:
        engine.dispose()
