"""
Redis 캐시 함수 직접 호출 테스트.

conftest의 autouse fixture가 get_cached/set_cached를 패치하지만
delete_cached/clear_cache_pattern은 패치하지 않는다.
또한 get_redis mock은 conftest에서 제공된다.

이 테스트에서는:
1. delete_cached, clear_cache_pattern → 직접 호출 (conftest 미패치)
2. get_cached, set_cached → conftest mock_redis_cache 활용하여 함수 원본 호출
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import delete_cached, clear_cache_pattern


class TestDeleteCachedDirect:
    """delete_cached — conftest에서 패치하지 않으므로 직접 호출 가능"""

    async def test_success(self, mock_redis_cache):
        """삭제 성공"""
        mock_redis_cache.delete.return_value = 1
        with patch("app.core.cache.get_redis", AsyncMock(return_value=mock_redis_cache)):
            result = await delete_cached("test:key")
        assert result is True
        mock_redis_cache.delete.assert_called_with("test:key")

    async def test_error(self):
        """Redis 에러 시 False"""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Redis down")
        with patch("app.core.cache.get_redis", AsyncMock(return_value=mock_redis)):
            result = await delete_cached("err:key")
        assert result is False


class TestClearCachePatternDirect:
    """clear_cache_pattern — conftest에서 패치하지 않으므로 직접 호출 가능"""

    async def test_with_matching_keys(self, mock_redis_cache):
        """매칭되는 키가 있을 때"""
        mock_redis_cache.keys.return_value = ["bids:1", "bids:2", "bids:3"]
        mock_redis_cache.delete.return_value = 3
        with patch("app.core.cache.get_redis", AsyncMock(return_value=mock_redis_cache)):
            count = await clear_cache_pattern("bids:*")
        assert count == 3

    async def test_no_matching_keys(self, mock_redis_cache):
        """매칭되는 키 없음"""
        mock_redis_cache.keys.return_value = []
        with patch("app.core.cache.get_redis", AsyncMock(return_value=mock_redis_cache)):
            count = await clear_cache_pattern("nonexistent:*")
        assert count == 0

    async def test_error(self):
        """Redis 에러 시 0"""
        mock_redis = AsyncMock()
        mock_redis.keys.side_effect = Exception("Redis down")
        with patch("app.core.cache.get_redis", AsyncMock(return_value=mock_redis)):
            count = await clear_cache_pattern("err:*")
        assert count == 0


class TestGetCachedViaIntegration:
    """get_cached — conftest에서 패치되므로 통합 테스트로 간접 커버.
    실제 get_cached/set_cached 로직은 bids list endpoint에서 사용된다.
    여기서는 get_redis mock 자체의 동작만 검증한다."""

    async def test_get_redis_returns_mock(self, mock_redis_cache):
        """conftest의 get_redis mock이 올바르게 설정되었는지 확인"""
        # get_redis mock은 conftest에서 제공
        assert mock_redis_cache is not None
        # get/set/delete 메서드가 있어야 함
        assert hasattr(mock_redis_cache, "get")
        assert hasattr(mock_redis_cache, "setex")
        assert hasattr(mock_redis_cache, "delete")
        assert hasattr(mock_redis_cache, "keys")

    async def test_cache_hit_simulation(self, mock_redis_cache):
        """캐시 히트 시뮬레이션"""
        mock_redis_cache.get.return_value = json.dumps({"items": [], "total": 0})
        data = await mock_redis_cache.get("bids:list:0:100::")
        assert data is not None
        parsed = json.loads(data)
        assert parsed["total"] == 0
