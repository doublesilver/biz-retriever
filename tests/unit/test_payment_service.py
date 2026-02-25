"""
PaymentService 단위 테스트
- 플랜 가격 조회
- 주문 ID/멱등성 키 생성
- 프로레이션 계산
- 웹훅 서명 검증
- 결제 생성/승인/취소/조회 (mock httpx)
"""

import hashlib
import hmac as hmac_mod
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    PaymentConfirmationError,
    PaymentError,
    PaymentNotConfiguredError,
)
from app.services.payment_service import PaymentService


class TestPaymentServiceConfig:
    """설정 관련"""

    def test_is_not_configured_without_key(self):
        service = PaymentService()
        if not service.secret_key:
            assert service.is_configured() is False

    def test_ensure_configured_raises(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            service._ensure_configured()


class TestPlanAmount:
    """플랜 가격 조회"""

    def test_free_plan(self):
        assert PaymentService().get_plan_amount("free") == 0

    def test_basic_plan(self):
        assert PaymentService().get_plan_amount("basic") == 10000

    def test_pro_plan(self):
        assert PaymentService().get_plan_amount("pro") == 30000

    def test_unknown_plan(self):
        assert PaymentService().get_plan_amount("enterprise") == 0


class TestOrderIdGeneration:
    """주문 ID 생성"""

    def test_format(self):
        service = PaymentService()
        order_id = service.generate_order_id(123, "basic")
        assert order_id.startswith("BIZ-123-BASIC-")
        parts = order_id.split("-")
        assert len(parts) == 5
        assert len(parts[3]) == 14
        assert len(parts[4]) == 8

    def test_uniqueness(self):
        service = PaymentService()
        ids = {service.generate_order_id(1, "basic") for _ in range(10)}
        assert len(ids) == 10


class TestIdempotencyKey:
    """멱등성 키"""

    def test_is_uuid(self):
        key = PaymentService.generate_idempotency_key()
        uuid.UUID(key)

    def test_uniqueness(self):
        keys = {PaymentService.generate_idempotency_key() for _ in range(10)}
        assert len(keys) == 10


class TestProration:
    """프로레이션(일할 계산)"""

    def test_upgrade_basic_to_pro(self):
        assert PaymentService().calculate_proration("basic", "pro", 15, 30) == 10000

    def test_downgrade_returns_zero(self):
        assert PaymentService().calculate_proration("pro", "basic", 15, 30) == 0

    def test_same_plan_returns_zero(self):
        assert PaymentService().calculate_proration("basic", "basic", 15, 30) == 0

    def test_zero_days(self):
        assert PaymentService().calculate_proration("basic", "pro", 0, 30) == 0

    def test_full_period(self):
        assert PaymentService().calculate_proration("basic", "pro", 30, 30) == 20000

    def test_zero_total_days(self):
        assert PaymentService().calculate_proration("basic", "pro", 15, 0) == 0


class TestWebhookSignature:
    """웹훅 HMAC-SHA256 서명 검증"""

    def test_no_secret_returns_true(self):
        service = PaymentService()
        service.webhook_secret = None
        assert service.verify_webhook_signature(b"payload", "any") is True

    def test_valid_signature(self):
        service = PaymentService()
        service.webhook_secret = "test-secret"
        payload = b'{"event": "test"}'
        expected = hmac_mod.new(b"test-secret", payload, hashlib.sha256).hexdigest()
        assert service.verify_webhook_signature(payload, expected) is True

    def test_invalid_signature(self):
        service = PaymentService()
        service.webhook_secret = "test-secret"
        assert service.verify_webhook_signature(b"payload", "wrong_sig") is False


class TestCreatePayment:
    """결제 요청 생성"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="
        service.client_key = "test_ck_123"

        result = await service.create_payment(
            amount=10000,
            order_id="BIZ-1-BASIC-test",
            order_name="Biz-Retriever BASIC",
            customer_email="test@example.com",
            customer_name="테스트",
        )
        assert result["amount"] == 10000
        assert result["client_key"] == "test_ck_123"
        assert "successUrl" in result

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.create_payment(
                amount=10000, order_id="t", order_name="t",
                customer_email="t@t.com", customer_name="t",
            )


class TestConfirmPayment:
    """결제 승인 (mock httpx)"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"paymentKey": "pk_test", "status": "DONE"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.confirm_payment("pk_test", "BIZ-1", 10000, "key")
        assert result["paymentKey"] == "pk_test"

    @pytest.mark.asyncio
    async def test_failure(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"code": "INVALID", "message": "오류"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentConfirmationError):
                await service.confirm_payment("pk", "BIZ-1", 10000)

    @pytest.mark.asyncio
    async def test_exception(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentConfirmationError):
                await service.confirm_payment("pk", "BIZ-1", 10000)

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.confirm_payment("pk", "BIZ-1", 10000)


class TestCancelPayment:
    """결제 취소"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "CANCELED"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.cancel_payment("pk_test", "사유")
        assert result["status"] == "CANCELED"

    @pytest.mark.asyncio
    async def test_failure(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"message": "이미 취소됨"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentError):
                await service.cancel_payment("pk", "사유")

    @pytest.mark.asyncio
    async def test_with_partial_amount(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "PARTIAL"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.cancel_payment("pk", "부분", cancel_amount=5000)
        assert result["status"] == "PARTIAL"

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.cancel_payment("pk", "사유")


class TestGetPaymentInfo:
    """결제 정보 조회"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"paymentKey": "pk", "amount": 10000}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.get_payment_info("pk")
        assert result["amount"] == 10000

    @pytest.mark.asyncio
    async def test_failure(self):
        service = PaymentService()
        service.auth_header = "Basic dGVzdDo="

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"message": "없음"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentError):
                await service.get_payment_info("pk_invalid")

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.get_payment_info("pk")
