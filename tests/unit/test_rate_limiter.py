"""
RateLimiter 단위 테스트
- Redis 미연결 시 동작
- check_rate_limit
- get_remaining
- rate_limit 데코레이터
"""

from unittest.mock import MagicMock

from app.services.rate_limiter import RateLimiter


class TestRateLimiterDisabled:
    """Redis 미연결 시"""

    def test_disabled_allows_all(self):
        limiter = RateLimiter()
        limiter.enabled = False
        assert limiter.check_rate_limit("key", 10, 60) is True

    def test_disabled_returns_max_remaining(self):
        limiter = RateLimiter()
        limiter.enabled = False
        assert limiter.get_remaining("key", 10) == 10


class TestCheckRateLimit:
    """check_rate_limit 테스트"""

    def test_first_request(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = None

        result = limiter.check_rate_limit("key", 10, 60)
        assert result is True
        limiter.redis_client.setex.assert_called_once_with("key", 60, 1)

    def test_within_limit(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "5"

        result = limiter.check_rate_limit("key", 10, 60)
        assert result is True
        limiter.redis_client.incr.assert_called_once_with("key")

    def test_at_limit(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "10"

        result = limiter.check_rate_limit("key", 10, 60)
        assert result is False

    def test_over_limit(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "15"

        result = limiter.check_rate_limit("key", 10, 60)
        assert result is False

    def test_redis_failure_allows(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.side_effect = Exception("Connection lost")

        result = limiter.check_rate_limit("key", 10, 60)
        assert result is True


class TestGetRemaining:
    """get_remaining 테스트"""

    def test_no_requests(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = None

        assert limiter.get_remaining("key", 10) == 10

    def test_some_used(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "3"

        assert limiter.get_remaining("key", 10) == 7

    def test_all_used(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "10"

        assert limiter.get_remaining("key", 10) == 0

    def test_over_limit_returns_zero(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.return_value = "15"

        assert limiter.get_remaining("key", 10) == 0

    def test_redis_failure_returns_max(self):
        limiter = RateLimiter()
        limiter.enabled = True
        limiter.redis_client = MagicMock()
        limiter.redis_client.get.side_effect = Exception("Connection lost")

        assert limiter.get_remaining("key", 10) == 10
