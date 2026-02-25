"""
로깅 모듈 단위 테스트
- SlackHandler
- add_app_context
- get_logger
- configure_logging
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch

from app.core.logging import SlackHandler, add_app_context, get_logger


class TestSlackHandler:
    """SlackHandler 테스트"""

    def test_emit_no_webhook(self):
        """webhook_url 없으면 무시"""
        handler = SlackHandler(webhook_url="")
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Test error", args=(), exc_info=None,
        )
        # 예외 없이 실행되면 성공
        handler.emit(record)

    def test_emit_with_webhook(self):
        """webhook_url 있으면 스레드 생성"""
        handler = SlackHandler(webhook_url="https://hooks.slack.com/test")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="Test error", args=(), exc_info=None,
        )
        record.asctime = "2026-01-01 00:00:00"

        with patch("app.core.logging.threading.Thread") as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance
            handler.emit(record)
            mock_thread.assert_called_once()
            mock_instance.start.assert_called_once()

    def test_send_payload_error(self):
        """_send_payload 실패 시 조용히 처리"""
        handler = SlackHandler(webhook_url="https://invalid-url")
        # 예외 없이 실행되면 성공
        with patch("app.core.logging.urlopen", side_effect=Exception("fail")):
            handler._send_payload({"text": "test"})


class TestAddAppContext:
    """add_app_context 프로세서 테스트"""

    def test_adds_service_and_environment(self):
        """서비스명과 환경 추가"""
        event_dict = {"event": "test_event"}
        result = add_app_context(None, None, event_dict)
        assert result["service"] == "biz-retriever"
        assert "environment" in result

    @patch.dict("os.environ", {"RAILWAY_ENVIRONMENT": "production"}, clear=False)
    def test_adds_railway_env(self):
        """Railway 환경 추가"""
        event_dict = {"event": "test_event"}
        result = add_app_context(None, None, event_dict)
        assert result.get("railway_env") == "production"


class TestGetLogger:
    """get_logger 테스트"""

    def test_returns_logger(self):
        """로거 인스턴스 반환"""
        log = get_logger("test_module")
        assert log is not None

    def test_default_name(self):
        """기본 이름으로 로거 반환"""
        log = get_logger()
        assert log is not None
