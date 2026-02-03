"""
Vercel Cron Job: G2B 크롤링
매일 08:00, 12:00, 18:00 실행

Full crawl logic from taskiq_tasks.py adapted for Vercel serverless.
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.models import BidAnnouncement, ExcludeKeyword, User, UserKeyword
from app.db.session import AsyncSessionLocal
from app.services.crawler_service import G2BCrawlerService
from app.services.notification_service import NotificationService
from app.services.rag_service import RAGService

# Vercel Cron Secret (보안)
CRON_SECRET = os.getenv("CRON_SECRET", "default-secret-change-me")

# Vercel timeout safety margin (50s of 60s max)
TIMEOUT_SECONDS = 50


async def handler(request: Request, authorization: str = Header(None)):
    """
    G2B 크롤링 Cron Job
    
    Vercel Cron에서 호출됨:
    - Schedule: "0 8,12,18 * * *" (08:00, 12:00, 18:00)
    - Authorization: Bearer <CRON_SECRET>
    
    Full logic from taskiq_tasks.py:
    - Dynamic keyword loading from DB
    - User keyword matching and notifications
    - AI analysis trigger for important bids (importance_score >= 2)
    """
    # Verify Cron Secret
    if not authorization or authorization != f"Bearer {CRON_SECRET}":
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    start_time = time.time()
    stats = {
        "total_crawled": 0,
        "new_saved": 0,
        "duplicates_skipped": 0,
        "notifications_sent": 0,
        "ai_analyzed": 0,
        "errors": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            # ============================================
            # 1. 동적 키워드 조회
            # ============================================
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

            # ============================================
            # 2. 크롤러 서비스 초기화
            # ============================================
            crawler = G2BCrawlerService()

            exclude_keywords = list(
                set(crawler.DEFAULT_EXCLUDE_KEYWORDS + list(dynamic_excludes))
            )
            include_keywords = list(dynamic_includes) or (
                crawler.INCLUDE_KEYWORDS_CONCESSION + crawler.INCLUDE_KEYWORDS_FLOWER
            )

            logger.info(
                f"크롤링 시작: include={len(include_keywords)}개, "
                f"exclude={len(exclude_keywords)}개"
            )

            # ============================================
            # 3. 크롤링 실행 (Async)
            # ============================================
            announcements = await crawler.fetch_new_announcements(
                exclude_keywords=exclude_keywords, include_keywords=include_keywords
            )

            stats["total_crawled"] = len(announcements)
            logger.info(f"G2B 크롤링 완료: {len(announcements)}건")

            if not announcements:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "No new announcements found",
                        "stats": stats,
                    },
                )

            # ============================================
            # 4. 활성 사용자 조회 (알림용)
            # ============================================
            stmt = (
                select(User)
                .where(User.is_active == True)
                .options(selectinload(User.full_profile), selectinload(User.keywords))
            )
            result = await session.execute(stmt)
            active_users = result.scalars().all()

            # ============================================
            # 5. 중복 체크를 위한 기존 URL 일괄 조회 (N+1 쿼리 방지)
            # ============================================
            announcement_urls = [a["url"] for a in announcements]
            stmt = select(BidAnnouncement.url).where(
                BidAnnouncement.url.in_(announcement_urls)
            )
            result = await session.execute(stmt)
            existing_urls = set(result.scalars().all())

            # ============================================
            # 6. 공고 저장 및 알림
            # ============================================
            rag_service = RAGService()

            for announcement_data in announcements:
                # Check timeout (safety margin)
                elapsed = time.time() - start_time
                if elapsed > TIMEOUT_SECONDS:
                    logger.warning(
                        f"Timeout approaching ({elapsed:.1f}s), stopping processing"
                    )
                    stats["errors"].append(
                        f"Timeout after processing {stats['new_saved']} bids"
                    )
                    break

                # 중복 체크 (메모리에서 조회)
                if announcement_data["url"] in existing_urls:
                    stats["duplicates_skipped"] += 1
                    continue

                try:
                    # 중요도 계산
                    importance_score = crawler.calculate_importance_score(
                        announcement_data
                    )
                    announcement_data["importance_score"] = importance_score

                    # DB 저장
                    new_announcement = BidAnnouncement(**announcement_data)
                    session.add(new_announcement)
                    await session.commit()
                    await session.refresh(new_announcement)
                    stats["new_saved"] += 1

                    logger.info(
                        f"새 공고 저장: {new_announcement.title} "
                        f"(중요도: {importance_score})"
                    )

                    # ============================================
                    # AI 분석 (중요 공고만, 시간 여유 있을 때만)
                    # ============================================
                    if importance_score >= 2 and (time.time() - start_time) < 40:
                        try:
                            full_text = f"{new_announcement.title} {new_announcement.content or ''}"
                            analysis_result = await rag_service.analyze_bid(full_text)

                            new_announcement.ai_summary = analysis_result.get("summary")
                            new_announcement.ai_keywords = analysis_result.get(
                                "keywords"
                            )
                            new_announcement.region_code = analysis_result.get(
                                "region_code"
                            )
                            new_announcement.license_requirements = analysis_result.get(
                                "license_requirements"
                            )
                            new_announcement.min_performance = analysis_result.get(
                                "min_performance"
                            )
                            new_announcement.processed = True

                            await session.commit()
                            stats["ai_analyzed"] += 1
                            logger.info(f"AI 분석 완료: {new_announcement.title}")
                        except Exception as e:
                            logger.error(f"AI 분석 실패: {e}")
                            stats["errors"].append(f"AI analysis failed: {str(e)[:50]}")

                    # ============================================
                    # 사용자별 키워드 매칭 알림
                    # ============================================
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
                            try:
                                await NotificationService.notify_bid_match(
                                    user, new_announcement, matched
                                )
                                stats["notifications_sent"] += 1
                                logger.info(
                                    f"알림 발송: User {user.id} -> Bid {new_announcement.id} "
                                    f"(키워드: {matched})"
                                )
                            except Exception as e:
                                logger.error(f"알림 발송 실패: {e}")
                                stats["errors"].append(
                                    f"Notification failed: {str(e)[:50]}"
                                )

                    # ============================================
                    # SSE/WebSocket 대체: 새 공고 로깅 (Vercel은 stateless)
                    # ============================================
                    # Note: WebSocket broadcast not available in serverless
                    # Clients should poll or use SSE endpoint separately
                    logger.info(
                        f"New bid broadcast (logged): "
                        f"id={new_announcement.id}, title={new_announcement.title}"
                    )

                except Exception as e:
                    logger.error(f"공고 처리 실패: {e}")
                    stats["errors"].append(f"Processing failed: {str(e)[:50]}")
                    continue

        elapsed_total = time.time() - start_time
        logger.info(
            f"크롤링 작업 완료: {stats['new_saved']}건 저장, "
            f"{stats['notifications_sent']}건 알림, "
            f"{elapsed_total:.1f}초 소요"
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Crawling completed successfully",
                "stats": stats,
                "elapsed_seconds": round(elapsed_total, 2),
            },
        )

    except Exception as e:
        logger.error(f"크롤링 작업 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "stats": stats,
            },
        )
