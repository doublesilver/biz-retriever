"""
AI 분석 API 엔드포인트 (Phase 3)
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_current_user
from app.db.models import BidAnnouncement, User
from app.db.session import get_db
from app.services.ml_service import ml_predictor
from app.services.rate_limiter import limiter

router = APIRouter()


@router.get("/predict-price/{announcement_id}")
@limiter.limit("20/minute")
async def predict_winning_price(
    request: Request,
    announcement_id: int = Path(..., ge=1, description="공고 ID (양수)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI 투찰가 예측 (Phase 6.2)
    과거 낙찰 데이터(BidResult)를 기반으로 최적 투찰가를 추천합니다.
    """
    logger.info(f"AI 투찰가 예측 요청: announcement_id={announcement_id}, user={current_user.email}")

    # 1. 공고 조회
    result = await session.execute(select(BidAnnouncement).where(BidAnnouncement.id == announcement_id))
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

    if not announcement.estimated_price:
        raise HTTPException(status_code=400, detail="추정가 정보가 없어 예측이 불가능합니다.")

    # 2. AI 예측 실행
    try:
        # ML 서비스 호출 (ml_predictor는 ml_service.py의 인스턴스)
        prediction = ml_predictor.predict_price(
            estimated_price=announcement.estimated_price,
            base_price=None,  # 나중에 DB 필드 추가 시 연동
            category=None,  # 공고 카테고리 정보가 있을 경우 추가
        )

        return {
            "announcement_id": announcement_id,
            "announcement_title": announcement.title,
            "estimated_price": announcement.estimated_price,
            "recommended_price": prediction["recommended_price"],
            "confidence": prediction["confidence"],
            "prediction_reason": "과거 유사 공고의 낙찰가 분포를 분석한 결과입니다.",
        }
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        # 모델이 학습되지 않았거나 데이터가 부족한 경우 Fallback (추정가의 88~90% 수준 제안)
        fallback_price = announcement.estimated_price * 0.88
        return {
            "announcement_id": announcement_id,
            "announcement_title": announcement.title,
            "estimated_price": announcement.estimated_price,
            "recommended_price": fallback_price,
            "confidence": 0.5,
            "prediction_reason": "충분한 학습 데이터가 없어 기본 요율(88%)을 적용했습니다.",
            "is_fallback": True,
        }


@router.get("/match/{announcement_id}")
@limiter.limit("30/minute")
async def check_match(
    request: Request,
    announcement_id: int = Path(..., ge=1, description="공고 ID (양수)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    공고 매칭 가능 여부 확인 (Hard Match)
    """
    # 1. 공고 조회
    result = await session.execute(select(BidAnnouncement).where(BidAnnouncement.id == announcement_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")

    # 2. 사용자 프로필 조회
    if not current_user.full_profile:
        raise HTTPException(status_code=400, detail="사용자 프로필이 없습니다.")

    # 3. 매칭 실행
    from app.services.matching_service import matching_service

    match_result = matching_service.check_hard_match(current_user.full_profile, bid)

    # Soft Match (Only if Hard Match is successful OR for information)
    # We allow seeing soft match score even if hard match fails, for debugging/insight
    soft_match_result = matching_service.calculate_soft_match(current_user.full_profile, bid)

    # 4. 제약 조건 정보 포함
    constraints = {
        "region_code": bid.region_code,
        "license_requirements": bid.license_requirements,
        "min_performance": bid.min_performance,
    }

    return {
        "bid_id": bid.id,
        "is_match": match_result["is_match"],
        "reasons": match_result["reasons"],
        "soft_match": {
            "score": soft_match_result["score"],
            "breakdown": soft_match_result["breakdown"],
        },
        "constraints": constraints,
    }


class SmartSearchRequest(BaseModel):
    query: str
    limit: int = 10


@router.post("/smart-search")
@limiter.limit("10/minute")
async def smart_search(
    http_request: Request,
    request: SmartSearchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    자연어 AI 스마트 검색
    - 사용자의 검색 의도를 분석하여 가장 관련성 높은 공고 순으로 정렬
    """
    logger.info(f"Smart Search: query='{request.query}', user={current_user.email}")

    try:
        # 1. 최근 공고 30개 가져오기 (성능을 위해 제한)
        stmt = select(BidAnnouncement).order_by(BidAnnouncement.created_at.desc()).limit(30)
        result = await session.execute(stmt)
        bids = result.scalars().all()

        if not bids:
            return {"results": []}

        # 2. 각 공고에 대해 시맨틱 점수 계산
        from app.services.matching_service import matching_service

        if not matching_service.client:
            logger.warning("Gemini client is not initialized in MatchingService")
            return {"error": "Gemini Client Not Initialized", "results": []}

        scored_results = []

        # 병렬 처리를 위해 task 리스트 생성
        tasks = [matching_service.calculate_semantic_match(request.query, bid) for bid in bids]
        results = await asyncio.gather(*tasks)

        for bid, result in zip(bids, results, strict=False):
            # result is {"score": float, "error": str}
            scored_results.append(
                {
                    "id": bid.id,
                    "title": bid.title,
                    "agency": bid.agency,
                    "relevance_score": result["score"],
                    "error": result.get("error"),  # Debug info
                    "created_at": bid.created_at,
                }
            )

        # 3. 점수 순으로 정렬 및 제한
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_results = scored_results[: request.limit]

        return {"query": request.query, "results": top_results}
    except Exception as e:
        logger.error(f"Smart Search Error: {str(e)}", exc_info=True)
        # A03: 트레이스백을 클라이언트에 노출하지 않음
        return {"error": "검색 처리 중 오류가 발생했습니다.", "results": []}
