"""
Redis 캐싱 유틸리티

fastapi-cache2 제거로 인해 Redis 직접 사용하여 캐싱 구현
"""

import json
from typing import Any, Optional

from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger

# Redis 클라이언트 (싱글톤)
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Redis 클라이언트 가져오기 (싱글톤)"""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,  # JSON 직렬화를 위해
        )
    return _redis_client


async def get_cached(key: str) -> Optional[Any]:
    """
    Redis에서 캐시된 데이터 조회

    Args:
        key: 캐시 키

    Returns:
        캐시된 데이터 (없으면 None)
    """
    try:
        redis = await get_redis()
        data = await redis.get(key)
        if data:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(data)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.error(f"Redis GET 오류: {e}")
        return None


async def set_cached(key: str, value: Any, expire: int = 300) -> bool:
    """
    Redis에 데이터 캐싱

    Args:
        key: 캐시 키
        value: 저장할 데이터 (JSON 직렬화 가능해야 함)
        expire: TTL (초 단위, 기본 5분)

    Returns:
        성공 여부
    """
    try:
        redis = await get_redis()

        # Pydantic 모델 직렬화 처리
        if isinstance(value, list):
            serialized = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in value
            ]
        elif hasattr(value, "model_dump"):
            serialized = value.model_dump()
        else:
            serialized = value

        await redis.setex(key, expire, json.dumps(serialized, ensure_ascii=False))
        logger.debug(f"Cache SET: {key} (expire={expire}s)")
        return True
    except Exception as e:
        logger.error(f"Redis SET 오류: {e}")
        return False


async def delete_cached(key: str) -> bool:
    """
    Redis에서 캐시 삭제

    Args:
        key: 캐시 키

    Returns:
        성공 여부
    """
    try:
        redis = await get_redis()
        await redis.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logger.error(f"Redis DELETE 오류: {e}")
        return False


async def clear_cache_pattern(pattern: str) -> int:
    """
    패턴에 매칭되는 모든 캐시 삭제

    Args:
        pattern: 캐시 키 패턴 (예: "bids:*")

    Returns:
        삭제된 키 개수
    """
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        if keys:
            count = await redis.delete(*keys)
            logger.info(f"Cache CLEAR: {pattern} ({count}개 키 삭제)")
            return count
        return 0
    except Exception as e:
        logger.error(f"Redis CLEAR 오류: {e}")
        return 0
