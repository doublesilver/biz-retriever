"""
NotificationService 단위 테스트
- Slack 메시지 전송
- 매칭 알림 (Slack + Email)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notification_service import NotificationService


class TestSendSlackMessage:
    """Slack 메시지 전송 테스트"""

    async def test_empty_webhook_returns_false(self):
        result = await NotificationService.send_slack_message("", "test")
        assert result is False

    async def test_none_webhook_returns_false(self):
        result = await NotificationService.send_slack_message(None, "test")
        assert result is False

    @patch("app.services.notification_service.httpx.AsyncClient")
    async def test_success(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await NotificationService.send_slack_message(
            "https://hooks.slack.com/test", "Test message"
        )
        assert result is True

    @patch("app.services.notification_service.httpx.AsyncClient")
    async def test_failure_status(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await NotificationService.send_slack_message(
            "https://hooks.slack.com/test", "Test message"
        )
        assert result is False

    @patch("app.services.notification_service.httpx.AsyncClient")
    async def test_exception_returns_false(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await NotificationService.send_slack_message(
            "https://hooks.slack.com/test", "Test message"
        )
        assert result is False


class TestNotifyBidMatch:
    """매칭 알림 테스트"""

    async def test_no_profile_skips(self):
        """프로필 없으면 알림 안 보냄"""
        user = MagicMock()
        user.full_profile = None

        bid = MagicMock()
        await NotificationService.notify_bid_match(user, bid, ["키워드1"])
        # 에러 없이 정상 반환

    @patch("app.services.notification_service.NotificationService.send_slack_message")
    async def test_slack_notification(self, mock_send):
        """Slack 알림 전송"""
        mock_send.return_value = True

        user = MagicMock()
        profile = MagicMock()
        profile.is_slack_enabled = True
        profile.slack_webhook_url = "https://hooks.slack.com/test"
        profile.is_email_enabled = False
        user.full_profile = profile

        bid = MagicMock()
        bid.title = "테스트 공고"
        bid.deadline = MagicMock()
        bid.estimated_price = 100000000
        bid.url = "https://example.com"

        await NotificationService.notify_bid_match(user, bid, ["키워드1"])
        mock_send.assert_called_once()

    @patch("app.services.notification_service.email_service")
    async def test_email_notification(self, mock_email):
        """이메일 알림 전송"""
        mock_email.send_bid_alert = AsyncMock(return_value=True)

        user = MagicMock()
        user.email = "test@example.com"
        profile = MagicMock()
        profile.is_slack_enabled = False
        profile.is_email_enabled = True
        profile.company_name = "테스트 기업"
        user.full_profile = profile

        bid = MagicMock()
        bid.id = 1
        bid.title = "테스트 공고"
        bid.agency = "테스트 기관"
        bid.deadline = MagicMock()
        bid.deadline.strftime.return_value = "2026-03-01 18:00"
        bid.estimated_price = 100000000
        bid.url = "https://example.com"
        bid.ai_summary = "AI 요약"

        await NotificationService.notify_bid_match(user, bid, ["키워드1"])
        mock_email.send_bid_alert.assert_called_once()
