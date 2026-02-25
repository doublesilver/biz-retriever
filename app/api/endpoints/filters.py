"""
필터 관리 API 엔드포인트 (Phase 2)
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logging import logger
from app.core.security import get_current_user
from app.db.models import User
from app.services.keyword_service import keyword_service
from app.services.rate_limiter import limiter

router = APIRouter()


class KeywordRequest(BaseModel):
    """제외 키워드 요청 스키마"""

    keyword: str = Field(..., min_length=1, max_length=50, description="제외 키워드")


@router.post("/keywords")
@limiter.limit("20/minute")
async def add_exclude_keyword(
    http_request: Request,
    request: KeywordRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(get_current_user),
):
    """
    제외 키워드 추가 (DB 저장 + 캐시 갱신)
    """
    try:
        keyword = await keyword_service.create_keyword(db, request.keyword)
        return {
            "message": f"'{keyword.word}' 제외 키워드에 추가되었습니다.",
            "id": keyword.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/keywords")
@limiter.limit("30/minute")
async def get_exclude_keywords(
    request: Request,
    active_only: bool = True,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    제외 키워드 목록 조회
    """
    if active_only:
        # 캐싱된 활성 키워드 (리스트)
        keywords = await keyword_service.get_active_keywords(db)
        return {"keywords": keywords}
    else:
        # 전체 키워드 (모델 리스트)
        keywords = await keyword_service.get_all_keywords(db)
        return {"keywords": [k.word for k in keywords]}


@router.delete("/keywords/{keyword}")
@limiter.limit("20/minute")
async def remove_exclude_keyword(
    request: Request,
    keyword: str = Path(..., min_length=1, max_length=50, description="삭제할 키워드"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(get_current_user),
):
    """
    제외 키워드 삭제
    """
    success = await keyword_service.delete_keyword(db, keyword)
    if not success:
        raise HTTPException(status_code=404, detail=f"'{keyword}'는 존재하지 않는 키워드입니다.")

    logger.info(f"제외 키워드 삭제: '{keyword}' by {current_user.email}")
    return {"message": f"'{keyword}' 제외 키워드에서 삭제되었습니다."}
