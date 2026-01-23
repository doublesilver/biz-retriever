"""
필터 관리 API 엔드포인트 (Phase 2)
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Body
from typing import List
from pydantic import BaseModel, Field
from redis import asyncio as aioredis
from app.core.config import settings
from app.core.security import get_current_user
from app.core.logging import logger
from app.db.models import User

router = APIRouter()

# Redis 연결
redis_client = None


async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = await aioredis.from_url(settings.REDIS_URL)
    return redis_client


class KeywordRequest(BaseModel):
    """제외 키워드 요청 스키마"""
    keyword: str = Field(..., min_length=1, max_length=50, description="제외 키워드")


@router.post("/exclude-keywords")
async def add_exclude_keyword(
    request: KeywordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    제외 키워드 추가

    - **keyword**: 제외할 키워드 (1-50자)

    Returns:
        추가 결과
    """
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="키워드는 공백일 수 없습니다.")

    redis = await get_redis()
    await redis.sadd("exclude_keywords", keyword)

    logger.info(f"제외 키워드 추가: '{keyword}' by {current_user.email}")

    return {"message": f"'{keyword}' 제외 키워드에 추가되었습니다."}


@router.get("/exclude-keywords")
async def get_exclude_keywords():
    """
    제외 키워드 목록 조회

    Returns:
        제외 키워드 리스트
    """
    redis = await get_redis()
    keywords = await redis.smembers("exclude_keywords")
    return {"keywords": [k.decode() for k in keywords]}


@router.delete("/exclude-keywords/{keyword}")
async def remove_exclude_keyword(
    keyword: str = Path(..., min_length=1, max_length=50, description="삭제할 키워드"),
    current_user: User = Depends(get_current_user)
):
    """
    제외 키워드 삭제

    - **keyword**: 삭제할 키워드 (1-50자)

    Returns:
        삭제 결과
    """
    redis = await get_redis()
    removed = await redis.srem("exclude_keywords", keyword)

    if removed == 0:
        raise HTTPException(status_code=404, detail=f"'{keyword}'는 존재하지 않는 키워드입니다.")

    logger.info(f"제외 키워드 삭제: '{keyword}' by {current_user.email}")

    return {"message": f"'{keyword}' 제외 키워드에서 삭제되었습니다."}
