"""
AI 분석 API 엔드포인트 (Phase 3)
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.core.logging import logger
from app.db.models import User, BidAnnouncement
from app.db.session import get_db
from app.services.ml_service import ml_predictor
from sqlalchemy import select

router = APIRouter()


@router.get("/predict-price/{announcement_id}")
async def predict_winning_price(
    announcement_id: int = Path(..., ge=1, description="공고 ID (양수)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    AI 투찰가 예측

    - **announcement_id**: 공고 ID (1 이상)

    Returns:
        예측 결과 (추천가, 신뢰도, 범위)
    """
    logger.info(f"투찰가 예측 요청: announcement_id={announcement_id}, user={current_user.email}")

    # 공고 조회
    result = await session.execute(
        select(BidAnnouncement).where(BidAnnouncement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

    if not announcement.estimated_price:
        raise HTTPException(status_code=400, detail="추정가 정보가 없습니다.")

    # 예측 실행
    prediction = ml_predictor.predict(
        estimated_price=announcement.estimated_price,
        expected_competition=3.5  # 기본 경쟁률
    )

    logger.info(f"투찰가 예측 완료: announcement_id={announcement_id}, recommended={prediction.get('recommended_price')}")

    return {
        "announcement_id": announcement_id,
        "announcement_title": announcement.title,
        "estimated_price": announcement.estimated_price,
        "prediction": prediction
    }
