"""
필터 관리 API 엔드포인트 (Phase 2)
"""
from fastapi import APIRouter, Depends
from typing import List
from redis import asyncio as aioredis
from app.core.config import settings
from app.core.security import get_current_user
from app.db.models import User

router = APIRouter()

# Redis 연결
redis_client = None

async def get_redis():
    global redis_client
    if not redis_client:
        redis_client = await aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        )
    return redis_client

@router.post("/exclude-keywords")
async def add_exclude_keyword(
    keyword: str,
    current_user: User = Depends(get_current_user)
):
    """
    제외 키워드 추가
    
    Args:
        keyword: 제외할 키워드
    
    Returns:
        추가 결과
    """
    redis = await get_redis()
    await redis.sadd("exclude_keywords", keyword)
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
    keyword: str,
    current_user: User = Depends(get_current_user)
):
    """
    제외 키워드 삭제
    
    Args:
        keyword: 삭제할 키워드
    
    Returns:
        삭제 결과
    """
    redis = await get_redis()
    await redis.srem("exclude_keywords", keyword)
    return {"message": f"'{keyword}' 제외 키워드에서 삭제되었습니다."}
