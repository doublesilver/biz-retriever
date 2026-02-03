"""
Payment Service 단위 테스트 (Tosspayments 통합)
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.payment_service import PaymentService


class TestPaymentService:
    """Tosspayments 결제 서비스 테스트"""

    # ============================================
    # 초기화 테스트
    # ============================================

    def test_init_with_credentials(self):
        """Tosspayments 자격증명으로 초기화"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_secret_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client_key"

            service = PaymentService()

            assert service.secret_key == "test_secret_key"
            assert service.client_key == "test_client_key"
            assert service.auth_header is not None
            assert service.auth_header.startswith("Basic ")

    def test_init_without_credentials(self):
        """자격증명 없이 초기화"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None

            service = PaymentService()

            assert service.secret_key is None
            assert service.auth_header is None

    def test_is_configured_true(self):
        """설정 확인 - 설정됨"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()
            assert service.is_configured() is True

    def test_is_configured_false(self):
        """설정 확인 - 미설정"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None

            service = PaymentService()
            assert service.is_configured() is False

    # ============================================
    # create_payment 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_payment_success(self):
        """결제 요청 생성 성공"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"
            mock_settings.FRONTEND_URL = "https://example.com"

            service = PaymentService()
            result = await service.create_payment(
                amount=10000,
                order_id="ORDER-001",
                order_name="Pro Plan",
                customer_email="user@example.com",
                customer_name="John Doe",
            )

            assert result["client_key"] == "test_client"
            assert result["amount"] == 10000
            assert result["orderId"] == "ORDER-001"
            assert result["orderName"] == "Pro Plan"
            assert result["customerEmail"] == "user@example.com"
            assert result["customerName"] == "John Doe"

    @pytest.mark.asyncio
    async def test_create_payment_not_configured(self):
        """결제 요청 생성 - 미설정 에러"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None

            service = PaymentService()

            with pytest.raises(ValueError, match="Tosspayments not configured"):
                await service.create_payment(
                    amount=10000,
                    order_id="ORDER-001",
                    order_name="Pro Plan",
                    customer_email="user@example.com",
                    customer_name="John Doe",
                )

    # ============================================
    # confirm_payment 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_confirm_payment_success(self):
        """결제 확인 성공"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "paymentKey": "PAY-001",
                "orderId": "ORDER-001",
                "status": "DONE",
            })

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                result = await service.confirm_payment(
                    payment_key="PAY-001", order_id="ORDER-001", amount=10000
                )

                assert result["paymentKey"] == "PAY-001"
                assert result["status"] == "DONE"

    @pytest.mark.asyncio
    async def test_confirm_payment_api_error(self):
        """결제 확인 - API 에러"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()

            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json = MagicMock(return_value={"message": "Invalid payment key"})

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                with pytest.raises(Exception, match="Payment failed"):
                    await service.confirm_payment(
                        payment_key="INVALID", order_id="ORDER-001", amount=10000
                    )

    @pytest.mark.asyncio
    async def test_confirm_payment_timeout(self):
        """결제 확인 - 타임아웃"""
        import httpx

        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(
                    side_effect=httpx.TimeoutException("Timeout")
                )
                mock_client_class.return_value = mock_client

                with pytest.raises(Exception, match="시간 초과"):
                    await service.confirm_payment(
                        payment_key="PAY-001", order_id="ORDER-001", amount=10000
                    )

    # ============================================
    # cancel_payment 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_cancel_payment_success(self):
        """결제 취소 성공"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "paymentKey": "PAY-001",
                "status": "CANCELED",
            })

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                result = await service.cancel_payment(
                    payment_key="PAY-001", cancel_reason="User requested"
                )

                assert result["status"] == "CANCELED"

    @pytest.mark.asyncio
    async def test_cancel_payment_not_configured(self):
        """결제 취소 - 미설정 에러"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = None
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = None

            service = PaymentService()

            with pytest.raises(ValueError, match="Tosspayments not configured"):
                await service.cancel_payment(
                    payment_key="PAY-001", cancel_reason="User requested"
                )

    # ============================================
    # get_payment_info 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_payment_info_success(self):
        """결제 정보 조회 성공"""
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.TOSSPAYMENTS_SECRET_KEY = "test_key"
            mock_settings.TOSSPAYMENTS_CLIENT_KEY = "test_client"

            service = PaymentService()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "paymentKey": "PAY-001",
                "orderId": "ORDER-001",
                "amount": 10000,
                "status": "DONE",
            })

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_client

                result = await service.get_payment_info(payment_key="PAY-001")

                assert result["paymentKey"] == "PAY-001"
                assert result["amount"] == 10000

    # ============================================
    # get_plan_amount 테스트
    # ============================================

    def test_get_plan_amount_free(self):
        """무료 플랜 가격 조회"""
        service = PaymentService()
        amount = service.get_plan_amount("free")
        assert amount == 0

    def test_get_plan_amount_basic(self):
        """기본 플랜 가격 조회"""
        service = PaymentService()
        amount = service.get_plan_amount("basic")
        assert amount == 10000

    def test_get_plan_amount_pro(self):
        """프로 플랜 가격 조회"""
        service = PaymentService()
        amount = service.get_plan_amount("pro")
        assert amount == 30000

    def test_get_plan_amount_invalid(self):
        """잘못된 플랜 가격 조회"""
        service = PaymentService()
        amount = service.get_plan_amount("invalid_plan")
        assert amount == 0

    # ============================================
    # generate_order_id 테스트
    # ============================================

    def test_generate_order_id_format(self):
        """주문 ID 생성 - 형식 확인"""
        service = PaymentService()
        order_id = service.generate_order_id(user_id=123, plan_name="pro")

        assert order_id.startswith("BIZ-123-PRO-")
        assert len(order_id) > 12  # BIZ-123-PRO- + timestamp

    def test_generate_order_id_unique(self):
        """주문 ID 생성 - 고유성 확인"""
        import time

        service = PaymentService()
        order_id_1 = service.generate_order_id(user_id=123, plan_name="pro")
        time.sleep(1.01)  # 1초 이상 지연 (초 단위 변경 필요)
        order_id_2 = service.generate_order_id(user_id=123, plan_name="pro")

        # 타임스탬프가 다르므로 다른 ID 생성
        assert order_id_1 != order_id_2
