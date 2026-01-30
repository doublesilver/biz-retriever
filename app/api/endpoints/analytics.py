"""
대시보드 분석 API
통계 및 인사이트 제공
"""

from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_current_user
from app.db.models import BidAnnouncement, User
from app.db.session import get_db

router = APIRouter()


@router.get("/summary")
async def get_analytics_summary(
    session: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Dict:
    """
    대시보드 통계 요약

    Returns:
        전체/주간/중요 공고 수, 평균 금액, TOP 기관 등
    """
    # 전체 공고 수
    total_result = await session.execute(select(func.count(BidAnnouncement.id)))
    total_bids = total_result.scalar()

    # 이번 주 공고 수
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_result = await session.execute(
        select(func.count(BidAnnouncement.id)).where(BidAnnouncement.created_at >= week_ago)
    )
    this_week = week_result.scalar()

    # 높은 중요도 (⭐⭐⭐)
    high_result = await session.execute(
        select(func.count(BidAnnouncement.id)).where(BidAnnouncement.importance_score == 3)
    )
    high_importance = high_result.scalar()

    # 평균 추정가
    avg_result = await session.execute(
        select(func.avg(BidAnnouncement.estimated_price)).where(BidAnnouncement.estimated_price.isnot(None))
    )
    average_price = avg_result.scalar() or 0

    # TOP 기관 (공고 많은 순)
    top_agencies_result = await session.execute(
        select(BidAnnouncement.agency, func.count(BidAnnouncement.id).label("count"))
        .where(BidAnnouncement.agency.isnot(None))
        .group_by(BidAnnouncement.agency)
        .order_by(func.count(BidAnnouncement.id).desc())
        .limit(5)
    )
    top_agencies = [{"name": row[0], "count": row[1]} for row in top_agencies_result.all()]

    # 출처별 분포
    source_result = await session.execute(
        select(BidAnnouncement.source, func.count(BidAnnouncement.id).label("count")).group_by(BidAnnouncement.source)
    )
    by_source = {row[0]: row[1] for row in source_result.all()}

    logger.info(f"Analytics 조회: total={total_bids}, week={this_week}")

    return {
        "total_bids": total_bids,
        "this_week": this_week,
        "high_importance": high_importance,
        "average_price": int(average_price),
        "top_agencies": top_agencies,
        "by_source": by_source,
        "trend": {"week_growth": round((this_week / max(total_bids - this_week, 1)) * 100, 1)},
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(default=30, ge=1, le=365, description="조회 기간 (1-365일)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict]:
    """
    공고 트렌드 데이터 (일별)

    - **days**: 조회 기간 (1-365일, 기본 30일)

    Returns:
        일별 공고 수 및 중요도별 분포
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # 일별 집계
    result = await session.execute(
        select(
            func.date(BidAnnouncement.created_at).label("date"),
            BidAnnouncement.importance_score,
            func.count(BidAnnouncement.id).label("count"),
        )
        .where(BidAnnouncement.created_at >= start_date)
        .group_by(func.date(BidAnnouncement.created_at), BidAnnouncement.importance_score)
        .order_by(func.date(BidAnnouncement.created_at))
    )

    # 데이터 재구성
    trends = {}
    for row in result.all():
        date_str = str(row[0])
        if date_str not in trends:
            trends[date_str] = {"date": date_str, "total": 0, "high": 0, "medium": 0, "low": 0}

        score = row[1]
        count = row[2]
        trends[date_str]["total"] += count

        if score == 3:
            trends[date_str]["high"] += count
        elif score == 2:
            trends[date_str]["medium"] += count
        else:
            trends[date_str]["low"] += count

    return list(trends.values())


@router.get("/deadline-alerts")
async def get_deadline_alerts(
    session: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """
    마감 임박 공고 목록

    Returns:
        24시간 이내 마감 예정 공고
    """
    now = datetime.utcnow()
    tomorrow = now + timedelta(hours=24)

    result = await session.execute(
        select(BidAnnouncement)
        .where(
            and_(
                BidAnnouncement.deadline.isnot(None),
                BidAnnouncement.deadline > now,
                BidAnnouncement.deadline <= tomorrow,
                BidAnnouncement.status.in_(["new", "reviewing", "bidding"]),
            )
        )
        .order_by(BidAnnouncement.deadline)
    )

    urgent_bids = result.scalars().all()

    return [
        {
            "id": bid.id,
            "title": bid.title,
            "agency": bid.agency,
            "deadline": bid.deadline.isoformat(),
            "hours_left": int((bid.deadline - now).total_seconds() / 3600),
            "importance_score": bid.importance_score,
            "url": bid.url,
        }
        for bid in urgent_bids
    ]
