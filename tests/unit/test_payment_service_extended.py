"""
PaymentService 확장 단위 테스트
- 플랜 가격 조회
- 프로레이션 계산
- 결제 설정 확인
- Webhook 서명 검증
- 주문 ID/멱등성 키 생성
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import PaymentNotConfiguredError
from app.services.payment_service import PaymentService


class TestPaymentServiceInit:
    """PaymentService 초기화 테스트"""

    def test_not_configured_without_key(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            service = PaymentService()
        assert service.is_configured() is False

    def test_configured_with_key(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_secret"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = "webhook_secret"
            service = PaymentService()
        assert service.is_configured() is True


class TestEnsureConfigured:
    """설정 확인 테스트"""

    def test_raises_when_not_configured(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            service = PaymentService()
        with pytest.raises(PaymentNotConfiguredError):
            service._ensure_configured()


class TestGetPlanAmount:
    """플랜 가격 조회"""

    def setup_method(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            self.service = PaymentService()

    def test_free_plan(self):
        assert self.service.get_plan_amount("free") == 0

    def test_basic_plan(self):
        assert self.service.get_plan_amount("basic") == 10000

    def test_pro_plan(self):
        assert self.service.get_plan_amount("pro") == 30000

    def test_unknown_plan(self):
        assert self.service.get_plan_amount("enterprise") == 0


class TestCalculateProration:
    """프로레이션 계산"""

    def setup_method(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            self.service = PaymentService()

    def test_upgrade_full_month(self):
        """basic → pro 30일 잔여"""
        amount = self.service.calculate_proration("basic", "pro", 30, 30)
        assert amount == 20000  # (30000 - 10000) * 30/30

    def test_upgrade_half_month(self):
        """basic → pro 15일 잔여"""
        amount = self.service.calculate_proration("basic", "pro", 15, 30)
        assert amount == 10000  # (30000 - 10000) * 15/30

    def test_downgrade_returns_zero(self):
        """다운그레이드 → 0"""
        amount = self.service.calculate_proration("pro", "basic", 15, 30)
        assert amount == 0

    def test_same_plan_returns_zero(self):
        amount = self.service.calculate_proration("basic", "basic", 15, 30)
        assert amount == 0

    def test_zero_total_days(self):
        amount = self.service.calculate_proration("basic", "pro", 15, 0)
        assert amount == 0


class TestGenerateOrderId:
    """주문 ID 생성"""

    def setup_method(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            self.service = PaymentService()

    def test_format(self):
        order_id = self.service.generate_order_id(1, "basic")
        assert order_id.startswith("BIZ-1-BASIC-")

    def test_unique(self):
        id1 = self.service.generate_order_id(1, "basic")
        id2 = self.service.generate_order_id(1, "basic")
        assert id1 != id2


class TestGenerateIdempotencyKey:
    """멱등성 키 생성"""

    def test_is_uuid_format(self):
        key = PaymentService.generate_idempotency_key()
        assert len(key) == 36  # UUID format
        assert "-" in key

    def test_unique(self):
        k1 = PaymentService.generate_idempotency_key()
        k2 = PaymentService.generate_idempotency_key()
        assert k1 != k2


class TestWebhookVerification:
    """웹훅 서명 검증"""

    def test_no_secret_returns_true(self):
        """시크릿 미설정 시 검증 건너뜀"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            service = PaymentService()
        result = service.verify_webhook_signature(b"payload", "signature")
        assert result is True

    def test_valid_signature(self):
        """유효한 서명 검증"""
        import hashlib
        import hmac

        secret = "test_webhook_secret"
        payload = b'{"type": "PAYMENT_CONFIRMED"}'
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = secret
            service = PaymentService()

        result = service.verify_webhook_signature(payload, expected)
        assert result is True

    def test_invalid_signature(self):
        """위변조된 서명"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = "test_secret"
            service = PaymentService()

        result = service.verify_webhook_signature(b"payload", "fake_signature")
        assert result is False


class TestCreatePayment:
    """결제 요청 데이터 생성"""

    async def test_not_configured_raises(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            service = PaymentService()
        with pytest.raises(PaymentNotConfiguredError):
            await service.create_payment(10000, "order-1", "상품명", "test@e.com", "홍길동")

    async def test_returns_correct_data(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "client_key"
            mock_settings.TOSSPAYMENTS_WEBHOOK_SECRET = None
            mock_settings.FRONTEND_URL = "https://example.com"
            service = PaymentService()

        result = await service.create_payment(
            10000, "order-1", "Basic 플랜", "test@e.com", "홍길동"
        )
        assert result["client_key"] == "client_key"
        assert result["amount"] == 10000
        assert result["orderId"] == "order-1"
        assert result["orderName"] == "Basic 플랜"
