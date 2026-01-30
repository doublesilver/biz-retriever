"""
Taskiq Background Tasks (Async-Native)

Celery tasks를 Taskiq로 변환 - async/await 네이티브 지원으로 더 간결하고 효율적
"""

import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.websocket import manager
from app.db.models import BidAnnouncement, ExcludeKeyword, User, UserKeyword
from app.db.session import AsyncSessionLocal
from app.services.crawler_service import G2BCrawlerService
from app.services.notification_service import NotificationService
from app.services.rag_service import RAGService
from app.worker.taskiq_app import broker

# ============================================
# G2B 크롤링 작업 (하루 3회)
# ============================================


@broker.task(
    task_name="crawl_g2b_bids",
    schedule=[
        {"cron": "0 8 * * *"},  # 매일 08:00
        {"cron": "0 12 * * *"},  # 매일 12:00
        {"cron": "0 18 * * *"},  # 매일 18:00
    ],
)
async def crawl_g2b_bids():
    """
    G2B 나라장터 크롤링 작업

    하루 3회 실행 (08:00, 12:00, 18:00)
    """
    logger.info("G2B 크롤링 작업 시작")

    async with AsyncSessionLocal() as session:
        # 1. 동적 키워드 조회
        stmt_exclude = select(ExcludeKeyword.word).where(
            ExcludeKeyword.is_active == True
        )
        result = await session.execute(stmt_exclude)
        dynamic_excludes = result.scalars().all()

        stmt_include = (
            select(UserKeyword.keyword)
            .where(UserKeyword.is_active == True, UserKeyword.category == "include")
            .distinct()
        )
        result = await session.execute(stmt_include)
        dynamic_includes = result.scalars().all()

        # 2. 크롤러 서비스 초기화
        crawler = G2BCrawlerService()

        exclude_keywords = list(
            set(crawler.DEFAULT_EXCLUDE_KEYWORDS + list(dynamic_excludes))
        )
        include_keywords = list(dynamic_includes) or (
            crawler.INCLUDE_KEYWORDS_CONCESSION + crawler.INCLUDE_KEYWORDS_FLOWER
        )

        # 3. 크롤링 실행 (Async)
        announcements = await crawler.fetch_new_announcements(
            exclude_keywords=exclude_keywords, include_keywords=include_keywords
        )

        logger.info(f"G2B 크롤링 완료: {len(announcements)}건")

        if not announcements:
            return

        # 4. 활성 사용자 조회 (알림용)
        stmt = (
            select(User)
            .where(User.is_active == True)
            .options(selectinload(User.full_profile), selectinload(User.keywords))
        )
        result = await session.execute(stmt)
        active_users = result.scalars().all()

        # 5. 공고 저장 및 알림
        for announcement_data in announcements:
            # 중복 체크
            stmt = select(BidAnnouncement).where(
                BidAnnouncement.url == announcement_data["url"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                continue

            # 중요도 계산
            importance_score = crawler.calculate_importance_score(announcement_data)
            announcement_data["importance_score"] = importance_score

            # DB 저장
            new_announcement = BidAnnouncement(**announcement_data)
            session.add(new_announcement)
            await session.commit()
            await session.refresh(new_announcement)

            # AI 분석 요청 (중요 공고만)
            if importance_score >= 2:
                await process_bid_analysis.kiq(new_announcement.id)

            # 사용자별 키워드 매칭 알림
            for user in active_users:
                if not user.keywords:
                    continue

                user_keywords = [
                    k.keyword
                    for k in user.keywords
                    if k.is_active and k.category == "include"
                ]

                if not user_keywords:
                    continue

                # 키워드 매칭 확인
                title = new_announcement.title
                content = new_announcement.content or ""
                full_text = f"{title} {content}"

                matched = [k for k in user_keywords if k in full_text]

                if matched:
                    await NotificationService.notify_bid_match(
                        user, new_announcement, matched
                    )
                    logger.info(
                        f"알림 발송: User {user.id} -> Bid {new_announcement.id} "
                        f"(키워드: {matched})"
                    )

            logger.info(
                f"새 공고 저장: {new_announcement.title} "
                f"(중요도: {importance_score})"
            )

            # WebSocket 브로드캐스트
            try:
                message = json.dumps(
                    {
                        "type": "new_bid",
                        "bid_id": new_announcement.id,
                        "title": new_announcement.title,
                        "agency": new_announcement.agency,
                    }
                )
                await manager.broadcast(message)
            except Exception as e:
                logger.error(f"WebSocket 브로드캐스트 실패: {e}")


# ============================================
# 모닝 브리핑 작업
# ============================================


@broker.task(
    task_name="send_morning_digest",
    schedule=[
        {"cron": "30 8 * * *"},  # 매일 08:30
    ],
)
async def send_morning_digest():
    """
    모닝 브리핑 전송

    밤사이(지난 12시간) 수집된 공고 요약
    """
    logger.info("모닝 브리핑 작업 시작")

    async with AsyncSessionLocal() as session:
        # 지난 12시간 공고 조회
        since = datetime.utcnow() - timedelta(hours=12)

        stmt = (
            select(BidAnnouncement)
            .where(BidAnnouncement.crawled_at >= since)
            .order_by(BidAnnouncement.importance_score.desc())
        )

        result = await session.execute(stmt)
        announcements = result.scalars().all()

        if announcements:
            # TODO: Slack 모닝 브리핑 전송
            # await NotificationService.send_digest(announcements)
            logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
        else:
            logger.info("모닝 브리핑: 새 공고 없음")


# ============================================
# AI 분석 작업
# ============================================


@broker.task(task_name="process_bid_analysis")
async def process_bid_analysis(bid_id: int):
    """
    공고 AI 분석 및 키워드 추출

    Args:
        bid_id: 분석할 공고 ID
    """
    logger.info(f"AI 분석 시작: Bid {bid_id}")

    async with AsyncSessionLocal() as session:
        # 1. 공고 조회
        stmt = select(BidAnnouncement).where(BidAnnouncement.id == bid_id)
        result = await session.execute(stmt)
        bid = result.scalar_one_or_none()

        if not bid:
            logger.error(f"분석 대상 공고 없음: {bid_id}")
            return

        # 2. AI 분석 (RAG Service)
        full_text = f"{bid.title} {bid.content}"

        rag = RAGService()
        analysis_result = await rag.analyze_bid(full_text)

        # 3. 결과 저장
        bid.ai_summary = analysis_result.get("summary")
        bid.ai_keywords = analysis_result.get("keywords")
        bid.region_code = analysis_result.get("region_code")
        bid.license_requirements = analysis_result.get("license_requirements")
        bid.min_performance = analysis_result.get("min_performance")
        bid.processed = True

        await session.commit()

        logger.info(f"AI 분석 완료: {bid.title}")
