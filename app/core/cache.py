"""
Redis 캐싱 유틸리티 (Stateless for Serverless)

Per-request connection pattern for serverless environments.
Graceful degradation when Redis unavailable.
"""

import json
from typing import Any, Optional

from redis import asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger


async def get_redis_client() -> Optional[aioredis.Redis]:
    """
    Create Redis connection for single request (stateless).

    Returns:
        Redis client or None if connection fails (graceful degradation)
    """
    try:
        client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None  # Graceful degradation


async def get_redis() -> Optional[aioredis.Redis]:
    """Alias for get_redis_client (backward compatibility)"""
    return await get_redis_client()


async def get_cached(key: str) -> Optional[Any]:
    """
    Redis에서 캐시된 데이터 조회 (stateless, graceful degradation)

    Args:
        key: 캐시 키

    Returns:
        캐시된 데이터 (없으면 None, Redis 실패시에도 None)
    """
    client = await get_redis_client()
    if client is None:
        return None  # Graceful degradation - cache miss

    try:
        data = await client.get(key)
        if data:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(data)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Redis GET failed: {e}")
        return None  # Graceful degradation
    finally:
        await client.aclose()


async def set_cached(key: str, value: Any, expire: Optional[int] = None) -> bool:
    """
    Redis에 데이터 캐싱 (stateless, graceful degradation)

    Args:
        key: 캐시 키
        value: 저장할 데이터 (JSON 직렬화 가능해야 함)
        expire: TTL (초 단위, None이면 config에서 기본값 사용)

    Returns:
        성공 여부 (Redis 실패시 False, 하지만 앱은 계속 동작)
    """
    client = await get_redis_client()
    if client is None:
        return False  # Graceful degradation - cache write skipped

    # Use TTL from config if not specified
    ttl = expire if expire is not None else settings.CACHE_DEFAULT_TTL

    try:
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

        await client.setex(key, ttl, json.dumps(serialized, ensure_ascii=False))
        logger.debug(f"Cache SET: {key} (expire={ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis SET failed: {e}")
        return False  # Graceful degradation
    finally:
        await client.aclose()


async def delete_cached(key: str) -> bool:
    """
    Redis에서 캐시 삭제 (stateless, graceful degradation)

    Args:
        key: 캐시 키

    Returns:
        성공 여부 (Redis 실패시 False)
    """
    client = await get_redis_client()
    if client is None:
        return False  # Graceful degradation

    try:
        await client.delete(key)
        logger.debug(f"Cache DELETE: {key}")
        return True
    except Exception as e:
        logger.warning(f"Redis DELETE failed: {e}")
        return False
    finally:
        await client.aclose()


async def clear_cache_pattern(pattern: str) -> int:
    """
    패턴에 매칭되는 모든 캐시 삭제 (stateless, graceful degradation)

    Args:
        pattern: 캐시 키 패턴 (예: "bids:*")

    Returns:
        삭제된 키 개수 (Redis 실패시 0)
    """
    client = await get_redis_client()
    if client is None:
        return 0  # Graceful degradation

    try:
        keys = await client.keys(pattern)
        if keys:
            count = await client.delete(*keys)
            logger.info(f"Cache CLEAR: {pattern} ({count} keys deleted)")
            return count
        return 0
    except Exception as e:
        logger.warning(f"Redis CLEAR failed: {e}")
        return 0
    finally:
        await client.aclose()
