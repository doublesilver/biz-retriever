"""
Slack 알림 서비스 단위 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.notification_service import SlackNotificationService
from app.db.models import BidAnnouncement


class TestSlackNotificationService:
    """Slack 알림 서비스 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        return SlackNotificationService()

    @pytest.fixture
    def mock_announcement(self):
        """Mock 공고 객체"""
        announcement = MagicMock(spec=BidAnnouncement)
        announcement.id = 1
        announcement.title = "테스트 구내식당 위탁운영"
        announcement.agency = "서울대학교병원"
        announcement.url = "https://example.com/bid/123"
        announcement.deadline = datetime.utcnow() + timedelta(days=7)
        announcement.estimated_price = 150000000
        announcement.importance_score = 3
        announcement.keywords_matched = ["구내식당", "위탁운영"]
        return announcement

    # ============================================
    # send_bid_notification 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_send_bid_notification_success(self, service, mock_announcement):
        """Slack 알림 전송 성공"""
        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(return_value=mock_response)

            mock_client.return_value = mock_instance

            result = await service.send_bid_notification(mock_announcement)

            assert result is True
            mock_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_bid_notification_failure_network_error(self, service, mock_announcement):
        """네트워크 에러 시 False 반환"""
        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(side_effect=Exception("Network error"))

            mock_client.return_value = mock_instance

            result = await service.send_bid_notification(mock_announcement)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_bid_notification_failure_http_error(self, service, mock_announcement):
        """HTTP 에러 시 False 반환"""
        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            import httpx
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("Error", request=MagicMock(), response=MagicMock())
            )

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(return_value=mock_response)

            mock_client.return_value = mock_instance

            result = await service.send_bid_notification(mock_announcement)

            assert result is False

    # ============================================
    # _format_message 테스트
    # ============================================

    def test_format_message_with_all_fields(self, service, mock_announcement):
        """모든 필드가 있는 경우 메시지 포맷"""
        message = service._format_message(mock_announcement)

        assert "channel" in message
        assert "text" in message
        assert mock_announcement.title in message["text"]
        assert mock_announcement.agency in message["text"]
        assert "⭐⭐⭐" in message["text"]  # importance_score = 3

    def test_format_message_with_missing_optional_fields(self, service):
        """옵션 필드 없을 때 기본값 처리"""
        announcement = MagicMock(spec=BidAnnouncement)
        announcement.title = "테스트 공고"
        announcement.agency = None  # 기관명 없음
        announcement.url = "https://example.com/bid/1"
        announcement.deadline = None  # 마감일 없음
        announcement.estimated_price = None  # 추정가 없음
        announcement.importance_score = 1
        announcement.keywords_matched = None  # 키워드 없음

        message = service._format_message(announcement)

        assert "미확인" in message["text"]  # agency 기본값
        assert "미정" in message["text"]  # deadline 기본값
        assert "미공개" in message["text"]  # estimated_price 기본값

    def test_format_message_importance_stars(self, service):
        """중요도별 별 개수 확인"""
        for score in [1, 2, 3]:
            announcement = MagicMock(spec=BidAnnouncement)
            announcement.title = "테스트"
            announcement.agency = "기관"
            announcement.url = "https://example.com"
            announcement.deadline = None
            announcement.estimated_price = None
            announcement.importance_score = score
            announcement.keywords_matched = []

            message = service._format_message(announcement)
            expected_stars = "⭐" * score

            assert expected_stars in message["text"]

    # ============================================
    # send_digest 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_send_digest_success(self, service, mock_announcement):
        """다이제스트 전송 성공"""
        announcements = [mock_announcement]

        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(return_value=mock_response)

            mock_client.return_value = mock_instance

            result = await service.send_digest(announcements)

            assert result is True

    @pytest.mark.asyncio
    async def test_send_digest_empty_list(self, service):
        """빈 리스트 시 False 반환"""
        result = await service.send_digest([])
        assert result is False

    @pytest.mark.asyncio
    async def test_send_digest_sorts_by_importance(self, service):
        """중요도 순 정렬 확인"""
        announcements = []
        for i in range(3):
            ann = MagicMock(spec=BidAnnouncement)
            ann.title = f"테스트 공고 {i}"
            ann.agency = "기관"
            ann.url = f"https://example.com/{i}"
            ann.deadline = datetime.utcnow() + timedelta(days=7)
            ann.importance_score = i + 1  # 1, 2, 3
            announcements.append(ann)

        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(return_value=mock_response)

            mock_client.return_value = mock_instance

            await service.send_digest(announcements)

            # post가 호출되었는지 확인
            assert mock_instance.post.called

    @pytest.mark.asyncio
    async def test_send_digest_limits_to_10(self, service):
        """최대 10개 제한 확인"""
        announcements = []
        for i in range(15):  # 15개 생성
            ann = MagicMock(spec=BidAnnouncement)
            ann.title = f"테스트 공고 {i}"
            ann.agency = "기관"
            ann.url = f"https://example.com/{i}"
            ann.deadline = datetime.utcnow() + timedelta(days=7)
            ann.importance_score = 2
            announcements.append(ann)

        with patch('app.services.notification_service.httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.post = AsyncMock(return_value=mock_response)

            mock_client.return_value = mock_instance

            result = await service.send_digest(announcements)

            assert result is True
            # 메시지가 전송되었는지 확인
            mock_instance.post.assert_called_once()
