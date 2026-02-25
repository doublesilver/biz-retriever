"""
PaymentService API 호출 테스트 (mock httpx)
- issue_billing_key: 성공, 실패, 미설정
- charge_billing_key: 성공, 실패, 멱등성 키, 미설정
- cancel_payment: exception 케이스
- get_payment_info: exception 케이스
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import (
    PaymentConfirmationError,
    PaymentError,
    PaymentNotConfiguredError,
)
from app.services.payment_service import PaymentService


def _make_configured_service():
    """설정된 PaymentService 인스턴스 생성"""
    service = PaymentService()
    service.auth_header = "Basic dGVzdDo="
    service.secret_key = "test_secret"
    return service


def _make_mock_client(response):
    """mock httpx AsyncClient 생성"""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestIssueBillingKey:
    """빌링키 발급 테스트"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = _make_configured_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "billingKey": "bk_test_123",
            "cardCompany": "신한카드",
        }
        mock_client = _make_mock_client(mock_resp)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.issue_billing_key("auth_key_123", "cust_key_123")

        assert result["billingKey"] == "bk_test_123"

    @pytest.mark.asyncio
    async def test_failure(self):
        service = _make_configured_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"message": "인증 실패"}
        mock_client = _make_mock_client(mock_resp)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentError):
                await service.issue_billing_key("auth_key", "cust_key")

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.issue_billing_key("auth_key", "cust_key")


class TestChargeBillingKey:
    """빌링키 자동 결제 테스트"""

    @pytest.mark.asyncio
    async def test_success(self):
        service = _make_configured_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"paymentKey": "pk_auto", "status": "DONE"}
        mock_client = _make_mock_client(mock_resp)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.charge_billing_key(
                billing_key="bk_test",
                amount=10000,
                order_id="BIZ-1-BASIC-test",
                order_name="Basic 구독 갱신",
                customer_email="test@example.com",
                customer_name="테스트",
            )
        assert result["status"] == "DONE"

    @pytest.mark.asyncio
    async def test_with_idempotency_key(self):
        service = _make_configured_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"paymentKey": "pk_auto", "status": "DONE"}
        mock_client = _make_mock_client(mock_resp)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.charge_billing_key(
                billing_key="bk_test",
                amount=10000,
                order_id="BIZ-1-BASIC-test",
                order_name="Basic 구독",
                customer_email="test@example.com",
                customer_name="테스트",
                idempotency_key="idem-key-123",
            )
        assert result["status"] == "DONE"

    @pytest.mark.asyncio
    async def test_failure(self):
        service = _make_configured_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"message": "잔액 부족"}
        mock_client = _make_mock_client(mock_resp)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentConfirmationError):
                await service.charge_billing_key(
                    billing_key="bk_test",
                    amount=10000,
                    order_id="BIZ-1",
                    order_name="Test",
                    customer_email="t@t.com",
                    customer_name="t",
                )

    @pytest.mark.asyncio
    async def test_not_configured(self):
        service = PaymentService()
        service.auth_header = None
        with pytest.raises(PaymentNotConfiguredError):
            await service.charge_billing_key(
                billing_key="bk",
                amount=10000,
                order_id="BIZ-1",
                order_name="t",
                customer_email="t@t.com",
                customer_name="t",
            )


class TestCancelPaymentException:
    """cancel_payment exception 경로 테스트"""

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        service = _make_configured_service()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Unexpected"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentError):
                await service.cancel_payment("pk_test", "사유")


class TestGetPaymentInfoException:
    """get_payment_info exception 경로 테스트"""

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        service = _make_configured_service()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("Unexpected"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.payment_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(PaymentError):
                await service.get_payment_info("pk_test")
