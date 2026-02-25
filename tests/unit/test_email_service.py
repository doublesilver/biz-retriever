"""
EmailService 단위 테스트
- 이메일 발송
- 템플릿 렌더링
- SendGrid 미설정 시 동작
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.email_service as email_mod
from app.services.email_service import EmailService


@pytest.fixture(autouse=True)
def _mock_sendgrid_classes():
    """sendgrid가 미설치 환경에서도 Mail/Email/To/Content를 사용할 수 있도록 mock 설정"""
    originals = {}
    names = ["Mail", "Email", "To", "Content", "Personalization"]
    for name in names:
        originals[name] = getattr(email_mod, name, None)
        if getattr(email_mod, name, None) is None:
            setattr(email_mod, name, MagicMock())
    yield
    for name in names:
        if originals[name] is None:
            # 원래 없었으면 삭제하거나 None으로 복원
            setattr(email_mod, name, None)
        else:
            setattr(email_mod, name, originals[name])


class TestEmailService:
    """EmailService 단위 테스트"""

    def test_email_service_not_configured(self):
        """SendGrid API 키 미설정 시 is_configured=False"""
        with patch.dict("os.environ", {"SENDGRID_API_KEY": ""}, clear=False):
            service = EmailService()
            assert service.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self):
        """미설정 상태에서 이메일 발송 시도 - False 반환"""
        service = EmailService()
        service.client = None

        result = await service.send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Test</p>",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_bulk_email_not_configured(self):
        """미설정 상태에서 대량 이메일 발송 시도 - 0 반환"""
        service = EmailService()
        service.client = None

        result = await service.send_bulk_email(
            recipients=["a@b.com", "c@d.com"],
            subject="Test",
            html_content="<p>Test</p>",
        )

        assert result == 0

    def test_render_bid_alert_email(self):
        """공고 알림 이메일 템플릿 렌더링"""
        service = EmailService()
        service.client = None

        html, plain = service.render_bid_alert_email(
            user_name="홍길동",
            bid_title="서울대병원 구내식당 위탁운영",
            bid_agency="서울대학교병원",
            bid_deadline="2026-03-01",
            bid_price="1억 5천만원",
            bid_url="https://example.com/bid/1",
            bid_summary="구내식당 위탁운영 입찰 공고입니다.",
            keywords=["구내식당", "위탁운영"],
        )

        assert "서울대병원" in html
        assert "홍길동" in html
        assert "구내식당" in html
        assert "위탁운영" in html
        assert "서울대병원" in plain
        assert "홍길동" in plain

    def test_render_bid_alert_email_minimal(self):
        """최소 데이터로 템플릿 렌더링"""
        service = EmailService()
        service.client = None

        html, plain = service.render_bid_alert_email(
            user_name="사용자",
            bid_title="테스트 공고",
            bid_agency="기관",
            bid_deadline="미정",
            bid_price="미정",
            bid_url="https://example.com",
        )

        assert "테스트 공고" in html
        assert "사용자" in plain

    @pytest.mark.asyncio
    async def test_send_bid_alert_not_configured(self):
        """미설정 상태에서 공고 알림 발송 - False 반환"""
        service = EmailService()
        service.client = None

        result = await service.send_bid_alert(
            to_email="test@example.com",
            user_name="사용자",
            bid_data={
                "title": "테스트",
                "agency": "기관",
                "deadline": "미정",
                "estimated_price": "1억",
                "url": "https://example.com",
            },
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """성공적인 이메일 발송"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_email(
            "test@example.com", "Test", "<p>Test</p>"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_plain_content(self):
        """plain text 포함 이메일 발송"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_email(
            "test@example.com", "Test", "<p>HTML</p>", "Plain text"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_failure_status(self):
        """비정상 상태 코드 반환"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.body = "Bad Request"
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_email(
            "test@example.com", "Test", "<p>Test</p>"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_exception(self):
        """발송 중 예외"""
        service = EmailService()
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception("Network Error")
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_email(
            "test@example.com", "Test", "<p>Test</p>"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_bulk_email_all_success(self):
        """대량 발송 - 모두 성공"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        count = await service.send_bulk_email(
            ["a@test.com", "b@test.com", "c@test.com"], "Sub", "<p>Body</p>"
        )
        assert count == 3

    @pytest.mark.asyncio
    async def test_send_subscription_notification(self):
        """구독 알림 이메일"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_subscription_notification(
            "test@example.com", "구독 갱신 완료", "<p>갱신</p>"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_invoice_receipt(self):
        """인보이스 영수증 이메일"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_invoice_receipt(
            to_email="test@example.com",
            user_name="테스트",
            invoice_number="INV-20260224-ABCD",
            plan_name="basic",
            amount=10000,
            billing_period="2026.02.24 ~ 2026.03.26",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_bid_alert_success(self):
        """공고 알림 발송 성공"""
        service = EmailService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        result = await service.send_bid_alert(
            to_email="test@example.com",
            user_name="홍길동",
            bid_data={
                "title": "서울시 정보통신 공사",
                "agency": "서울시청",
                "deadline": "2026-03-01",
                "estimated_price": "5억",
                "url": "https://example.com/bid/1",
                "ai_summary": "정보통신 관련 공사",
                "keywords_matched": ["정보통신", "공사"],
            },
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_bulk_email_partial_failure(self):
        """대량 발송 - 일부 실패"""
        service = EmailService()
        mock_client = MagicMock()
        # 첫 번째 성공, 두 번째 실패, 세 번째 성공
        r_success = MagicMock()
        r_success.status_code = 202
        r_fail = MagicMock()
        r_fail.status_code = 400
        r_fail.body = "Bad Request"
        mock_client.send.side_effect = [r_success, r_fail, r_success]
        service.client = mock_client
        service.from_email = "test@test.com"
        service.from_name = "Test"

        count = await service.send_bulk_email(
            ["a@test.com", "b@test.com", "c@test.com"], "Sub", "<p>Body</p>"
        )
        assert count == 2
