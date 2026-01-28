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
    prediction_price = ml_predictor.predict_price(
        estimated_price=announcement.estimated_price
        # category field missing in BidAnnouncement
    )

    prediction = {
        "recommended_price": prediction_price,
        "confidence": 0.8 # Dummy
    }

    logger.info(f"투찰가 예측 완료: announcement_id={announcement_id}, recommended={prediction.get('recommended_price')}")

    return {
        "announcement_id": announcement_id,
        "announcement_title": announcement.title,
        "estimated_price": announcement.estimated_price,
        "prediction": prediction
    }


@router.get("/match/{announcement_id}")
async def check_match(
    announcement_id: int = Path(..., ge=1, description="공고 ID (양수)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    공고 매칭 가능 여부 확인 (Hard Match)
    """
    # 1. 공고 조회
    result = await session.execute(
        select(BidAnnouncement).where(BidAnnouncement.id == announcement_id)
    )
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

    # 2. 사용자 프로필 조회
    if not current_user.profile:
        raise HTTPException(status_code=400, detail="사용자 프로필이 없습니다.")
    
    # 3. 매칭 실행
    from app.services.matching_service import matching_service
    match_result = matching_service.check_hard_match(current_user.profile, bid)
    
    # Soft Match (Only if Hard Match is successful OR for information)
    # We allow seeing soft match score even if hard match fails, for debugging/insight
    soft_match_result = matching_service.calculate_soft_match(current_user.profile, bid)
    
    # 4. 제약 조건 정보 포함
    constraints = {
        "region_code": bid.region_code,
        "license_requirements": bid.license_requirements,
        "min_performance": bid.min_performance
    }
    
    return {
        "bid_id": bid.id,
        "is_match": match_result["is_match"],
        "reasons": match_result["reasons"],
        "soft_match": {
            "score": soft_match_result["score"],
            "breakdown": soft_match_result["breakdown"]
        },
        "constraints": constraints
    }
