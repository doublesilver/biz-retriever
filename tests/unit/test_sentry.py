"""
Sentry 설정 단위 테스트
- init_sentry: DSN 미설정, DSN 설정
- _before_send: 필터링 로직
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.sentry import _before_send, init_sentry


class TestBeforeSend:
    """_before_send 민감정보 필터링 테스트"""

    def test_filters_404_error(self):
        """404 에러는 None 반환 (전송하지 않음)"""
        exc = MagicMock()
        exc.status_code = 404
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send({}, hint)
        assert result is None

    def test_filters_429_error(self):
        """429 에러는 None 반환"""
        exc = MagicMock()
        exc.status_code = 429
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send({}, hint)
        assert result is None

    def test_passes_500_error(self):
        """500 에러는 통과"""
        exc = MagicMock()
        exc.status_code = 500
        event = {"some": "data"}
        hint = {"exc_info": (type(exc), exc, None)}
        result = _before_send(event, hint)
        assert result is not None

    def test_filters_authorization_header(self):
        """Authorization 헤더 필터링"""
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret_token",
                    "Content-Type": "application/json",
                }
            }
        }
        result = _before_send(event, {})
        assert result["request"]["headers"]["Authorization"] == "[Filtered]"
        assert result["request"]["headers"]["Content-Type"] == "application/json"

    def test_filters_cookie_header(self):
        """Cookie 헤더 필터링"""
        event = {
            "request": {
                "headers": {
                    "Cookie": "session=secret123",
                }
            }
        }
        result = _before_send(event, {})
        assert result["request"]["headers"]["Cookie"] == "[Filtered]"

    def test_filters_api_key_header(self):
        """X-API-Key 헤더 필터링"""
        event = {
            "request": {
                "headers": {
                    "X-API-Key": "api_key_secret",
                }
            }
        }
        result = _before_send(event, {})
        assert result["request"]["headers"]["X-API-Key"] == "[Filtered]"

    def test_filters_password_in_body(self):
        """요청 body에서 password 필터링"""
        event = {
            "request": {
                "data": {
                    "email": "user@example.com",
                    "password": "secret_password",
                }
            }
        }
        result = _before_send(event, {})
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["email"] == "user@example.com"

    def test_filters_multiple_sensitive_fields(self):
        """여러 민감 필드 필터링"""
        event = {
            "request": {
                "data": {
                    "password": "secret",
                    "secret_key": "sk_123",
                    "api_key": "ak_123",
                    "token": "tok_123",
                    "username": "user",
                }
            }
        }
        result = _before_send(event, {})
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["secret_key"] == "[Filtered]"
        assert result["request"]["data"]["api_key"] == "[Filtered]"
        assert result["request"]["data"]["token"] == "[Filtered]"
        assert result["request"]["data"]["username"] == "user"

    def test_no_request_field_passes(self):
        """request 필드 없는 이벤트는 그대로 통과"""
        event = {"message": "Test error"}
        result = _before_send(event, {})
        assert result == {"message": "Test error"}

    def test_no_exc_info_passes(self):
        """exc_info 없는 hint는 이벤트 통과"""
        event = {"level": "error"}
        result = _before_send(event, {})
        assert result == {"level": "error"}

    def test_exc_without_status_code(self):
        """status_code 속성 없는 예외는 통과"""
        exc = ValueError("test")
        hint = {"exc_info": (type(exc), exc, None)}
        event = {"message": "error"}
        result = _before_send(event, hint)
        assert result is not None


class TestInitSentry:
    """init_sentry 테스트"""

    @patch("app.core.sentry.sentry_sdk")
    @patch.dict("os.environ", {"SENTRY_DSN": ""}, clear=False)
    def test_no_dsn_does_not_init(self, mock_sdk):
        """DSN 미설정 시 초기화하지 않음"""
        # Clear SENTRY_DSN
        import os
        original = os.environ.pop("SENTRY_DSN", None)
        try:
            init_sentry()
            mock_sdk.init.assert_not_called()
        finally:
            if original:
                os.environ["SENTRY_DSN"] = original

    @patch("app.core.sentry.sentry_sdk")
    @patch.dict("os.environ", {"SENTRY_DSN": "https://test@sentry.io/123"}, clear=False)
    def test_with_dsn_calls_init(self, mock_sdk):
        """DSN 설정 시 초기화 호출"""
        init_sentry()
        mock_sdk.init.assert_called_once()
        call_kwargs = mock_sdk.init.call_args[1]
        assert call_kwargs["dsn"] == "https://test@sentry.io/123"
        assert call_kwargs["before_send"] == _before_send
