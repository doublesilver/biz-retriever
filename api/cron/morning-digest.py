"""
Vercel Cron Job: 모닝 브리핑 (Morning Digest)
매일 08:30 실행 - 밤사이(지난 12시간) 수집된 공고 요약
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from fastapi import Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from app.db.models import BidAnnouncement
from app.db.session import AsyncSessionLocal
from app.services.notification_service import NotificationService
from app.core.logging import logger


# Vercel Cron Secret (보안)
CRON_SECRET = os.getenv("CRON_SECRET", "default-secret-change-me")


async def handler(request: Request, authorization: str = Header(None)):
    """
    모닝 브리핑 Cron Job
    
    Vercel Cron에서 호출됨:
    - Schedule: "30 8 * * *" (매일 08:30 UTC)
    - Authorization: Bearer <CRON_SECRET>
    
    기능:
    - 지난 12시간 동안 수집된 공고 조회
    - 중요도 순으로 정렬
    - Slack 모닝 브리핑 전송
    """
    # Verify Cron Secret
    if not authorization or authorization != f"Bearer {CRON_SECRET}":
        logger.warning(f"Unauthorized morning digest request: {authorization}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"}
        )
    
    try:
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
            
            logger.info(f"모닝 브리핑: {len(announcements)}건 공고 조회")
            
            if not announcements:
                logger.info("모닝 브리핑: 새 공고 없음")
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "total": 0,
                        "message": "No new announcements in the last 12 hours"
                    }
                )
            
            # Slack 모닝 브리핑 전송
            await send_morning_digest_slack(announcements)
            
            logger.info(f"모닝 브리핑 전송 완료: {len(announcements)}건")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "total": len(announcements),
                    "message": "Morning digest sent successfully"
                }
            )
    
    except Exception as e:
        logger.error(f"모닝 브리핑 오류: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


async def send_morning_digest_slack(announcements: list):
    """
    Slack 모닝 브리핑 메시지 전송
    
    Args:
        announcements: BidAnnouncement 객체 리스트
    """
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    if not slack_webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping Slack notification")
        return
    
    # 상위 5개 공고만 표시
    top_announcements = announcements[:5]
    
    # 공고 목록 포맷팅
    announcements_text = ""
    for idx, bid in enumerate(top_announcements, 1):
        importance_emoji = "⭐" * bid.importance_score if bid.importance_score else "☆"
        price_str = f"{bid.estimated_price:,.0f}원" if bid.estimated_price else "미정"
        deadline_str = bid.deadline.strftime("%m/%d") if bid.deadline else "미정"
        
        announcements_text += (
            f"{idx}. {importance_emoji} *{bid.title}*\n"
            f"   기관: {bid.agency}\n"
            f"   마감: {deadline_str} | 추정가: {price_str}\n"
            f"   <{bid.url}|공고 보기>\n\n"
        )
    
    # Slack 메시지 구성
    message = (
        f"🌅 *모닝 브리핑 - {datetime.now().strftime('%m월 %d일')}*\n"
        f"지난 12시간 동안 수집된 공고 {len(announcements)}건\n\n"
        f"{announcements_text}"
        f"<https://biz-retriever.vercel.app|대시보드 보기>"
    )
    
    # Slack 전송
    success = await NotificationService.send_slack_message(slack_webhook_url, message)
    
    if success:
        logger.info("Slack 모닝 브리핑 전송 성공")
    else:
        logger.error("Slack 모닝 브리핑 전송 실패")
