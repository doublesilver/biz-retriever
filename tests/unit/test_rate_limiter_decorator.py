"""
rate_limit 데코레이터 단위 테스트
- 정상 요청
- Rate limit 초과
- 응답에 헤더 추가
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestRateLimitDecorator:
    """rate_limit 데코레이터 테스트"""

    async def test_normal_request(self):
        """정상 요청 → 원래 함수 실행"""
        from app.services.rate_limiter import rate_limit, rate_limiter

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_response = MagicMock()
        mock_response.headers = {}

        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint(request):
            return mock_response

        with patch.object(rate_limiter, "check_rate_limit", return_value=True):
            with patch.object(rate_limiter, "get_remaining", return_value=9):
                result = await my_endpoint(mock_request)

        assert result == mock_response
        assert result.headers["X-RateLimit-Limit"] == "10"
        assert result.headers["X-RateLimit-Remaining"] == "9"

    async def test_exceeded(self):
        """Rate limit 초과 → 429"""
        from app.services.rate_limiter import rate_limit, rate_limiter

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        @rate_limit(max_requests=5, window_seconds=30)
        async def my_endpoint(request):
            return {"ok": True}

        with patch.object(rate_limiter, "check_rate_limit", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await my_endpoint(mock_request)

        assert exc_info.value.status_code == 429

    async def test_response_without_headers(self):
        """headers 속성 없는 응답"""
        from app.services.rate_limiter import rate_limit, rate_limiter

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"

        @rate_limit(max_requests=10, window_seconds=60)
        async def my_endpoint(request):
            return {"data": "no headers attr"}

        with patch.object(rate_limiter, "check_rate_limit", return_value=True):
            with patch.object(rate_limiter, "get_remaining", return_value=9):
                result = await my_endpoint(mock_request)

        # dict has no headers attribute, so no error
        assert result == {"data": "no headers attr"}
