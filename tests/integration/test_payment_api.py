"""
Payment API 통합 테스트
- /api/v1/payment/plans (공개)
- /api/v1/payment/subscription (인증 필요)
- /api/v1/payment/create (인증 필요, payment 미설정 시)
- /api/v1/payment/confirm (인증 필요, payment 미설정 시)
- /api/v1/payment/cancel (인증 필요)
- /api/v1/payment/history (인증 필요)
- /api/v1/payment/invoices (인증 필요)
- /api/v1/payment/webhook (서명 검증)
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentHistory, Subscription


class TestPaymentPlans:
    """플랜 목록 조회"""

    async def test_get_plans(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/payment/plans")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        plans = data["data"]
        assert len(plans) == 3
        names = [p["name"] for p in plans]
        assert "free" in names
        assert "basic" in names
        assert "pro" in names


class TestPaymentSubscription:
    """구독 상태 조회"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/payment/subscription")
        assert response.status_code == 401

    async def test_get_subscription_status(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/payment/subscription")
        # 구독이 없으면 기본 응답 또는 에러 반환
        assert response.status_code in [200, 404]


class TestCreatePayment:
    """결제 생성"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/create",
            json={"plan_name": "basic"},
        )
        assert response.status_code == 401

    async def test_payment_not_configured(self, authenticated_client: AsyncClient):
        """payment_service가 미설정 시 PaymentNotConfiguredError"""
        response = await authenticated_client.post(
            "/api/v1/payment/create",
            json={"plan_name": "basic"},
        )
        # PaymentNotConfiguredError → 503
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False

    async def test_invalid_plan(self, authenticated_client: AsyncClient):
        """유효하지 않은 플랜명"""
        response = await authenticated_client.post(
            "/api/v1/payment/create",
            json={"plan_name": "enterprise"},
        )
        assert response.status_code == 422


class TestConfirmPayment:
    """결제 승인"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/confirm",
            json={"paymentKey": "pk_test", "orderId": "BIZ-1-BASIC-test", "amount": 10000},
        )
        assert response.status_code == 401

    async def test_payment_not_configured(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post(
            "/api/v1/payment/confirm",
            json={"paymentKey": "pk_test", "orderId": "BIZ-1-BASIC-test", "amount": 10000},
        )
        assert response.status_code == 503


class TestCancelPayment:
    """결제 취소"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/cancel",
            json={"paymentKey": "pk_test", "cancelReason": "사유"},
        )
        assert response.status_code == 401

    async def test_payment_not_configured(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post(
            "/api/v1/payment/cancel",
            json={"paymentKey": "pk_test", "cancelReason": "환불 요청"},
        )
        assert response.status_code == 503


class TestPaymentHistory:
    """결제 이력"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/payment/history")
        assert response.status_code == 401

    async def test_empty_history(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/payment/history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["meta"]["total"] == 0


class TestPaymentInvoices:
    """인보이스 조회"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/payment/invoices")
        assert response.status_code == 401

    async def test_empty_invoices(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/payment/invoices")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []


class TestPaymentWebhook:
    """웹훅 핸들러"""

    async def test_missing_signature(self, async_client: AsyncClient):
        """서명 누락 시 (webhook_secret 미설정이면 pass)"""
        response = await async_client.post(
            "/api/v1/payment/webhook",
            json={
                "eventType": "PAYMENT_DONE",
                "data": {"paymentKey": "pk_test", "status": "DONE"},
            },
        )
        # webhook_secret 미설정이면 서명 검증 skip, payment_not_found 반환
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["processed"] is False

    async def test_missing_payment_key(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/webhook",
            json={"eventType": "PAYMENT_DONE", "data": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["processed"] is False
        assert data["data"]["reason"] == "missing_payment_key"


class TestSubscriptionCancel:
    """구독 해지"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/subscription/cancel",
            json={"reason": "더 이상 필요없음"},
        )
        assert response.status_code == 401


class TestChangePlan:
    """플랜 변경"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/payment/subscription/change-plan",
            json={"new_plan": "pro"},
        )
        assert response.status_code == 401

    async def test_no_subscription(self, authenticated_client: AsyncClient):
        """구독이 없는 사용자의 플랜 변경 시도"""
        response = await authenticated_client.post(
            "/api/v1/payment/subscription/change-plan",
            json={"new_plan": "pro"},
        )
        # SubscriptionNotFoundError
        assert response.status_code in [404, 400]

    async def test_invalid_plan_name(self, authenticated_client: AsyncClient):
        """유효하지 않은 플랜명 - 422"""
        response = await authenticated_client.post(
            "/api/v1/payment/subscription/change-plan",
            json={"new_plan": "enterprise"},
        )
        assert response.status_code == 422


class TestSubscriptionStatus:
    """구독 상태 상세"""

    async def test_with_subscription(
        self, authenticated_client: AsyncClient, test_subscription
    ):
        """구독이 있는 경우 상태 조회"""
        response = await authenticated_client.get("/api/v1/payment/subscription")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestPaymentHistoryWithData:
    """결제 이력 (데이터 포함)"""

    async def test_with_pagination(self, authenticated_client: AsyncClient):
        """페이지네이션 파라미터"""
        response = await authenticated_client.get(
            "/api/v1/payment/history?skip=0&limit=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestInvoiceDetail:
    """인보이스 상세"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/payment/invoices/INV-2026-001")
        assert response.status_code == 401

    async def test_not_found(self, authenticated_client: AsyncClient):
        """존재하지 않는 인보이스"""
        response = await authenticated_client.get(
            "/api/v1/payment/invoices/INV-NONEXIST-999"
        )
        assert response.status_code == 404


class TestSubscriptionCancelWithSub:
    """구독 해지 (구독 있는 상태)"""

    async def test_cancel_no_subscription(self, authenticated_client: AsyncClient):
        """구독이 없는 사용자의 해지 시도"""
        response = await authenticated_client.post(
            "/api/v1/payment/subscription/cancel",
            json={"reason": "테스트 해지"},
        )
        # SubscriptionNotFoundError
        assert response.status_code in [404, 400]


# ============================================
# Mocked Payment Service Tests
# ============================================


class TestCreatePaymentMocked:
    """결제 생성 (payment_service 모킹)"""

    async def test_create_payment_success(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """결제 생성 성공"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True
            mock_ps.get_plan_amount.return_value = 10000
            mock_ps.generate_order_id.return_value = "BIZ-1-BASIC-20260224-abc"
            mock_ps.create_payment = AsyncMock(return_value={
                "client_key": "ck_test",
                "amount": 10000,
                "orderId": "BIZ-1-BASIC-20260224-abc",
            })

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_ss.get_subscription = AsyncMock(return_value=None)

                response = await authenticated_client.post(
                    "/api/v1/payment/create",
                    json={"plan_name": "basic"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    async def test_create_payment_free_plan(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """무료 플랜 결제 시도 - 400"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True
            mock_ps.get_plan_amount.return_value = 0

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_ss.get_subscription = AsyncMock(return_value=None)

                response = await authenticated_client.post(
                    "/api/v1/payment/create",
                    json={"plan_name": "basic"},
                )
                assert response.status_code == 400

    async def test_create_payment_duplicate_subscription(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """이미 같은 플랜 구독 중 - DuplicateSubscriptionError"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True

            mock_sub = MagicMock()
            mock_sub.plan_name = "basic"
            mock_sub.is_active = True
            mock_sub.status = "active"

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_ss.get_subscription = AsyncMock(return_value=mock_sub)

                response = await authenticated_client.post(
                    "/api/v1/payment/create",
                    json={"plan_name": "basic"},
                )
                assert response.status_code == 409


class TestConfirmPaymentMocked:
    """결제 승인 (payment_service 모킹)"""

    async def test_confirm_success(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """결제 승인 성공"""
        mock_sub = MagicMock()
        mock_sub.next_billing_date = datetime.utcnow() + timedelta(days=30)

        mock_invoice = MagicMock()
        mock_invoice.invoice_number = "INV-2026-001"

        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True
            mock_ps.get_plan_amount.return_value = 10000
            mock_ps.generate_idempotency_key.return_value = "idemp-key-123"
            mock_ps.confirm_payment = AsyncMock(return_value={"status": "DONE"})

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_ss.create_subscription = AsyncMock(return_value=mock_sub)

                with patch("app.api.endpoints.payment.invoice_service") as mock_inv:
                    mock_inv.create_invoice = AsyncMock(return_value=mock_invoice)
                    mock_inv.mark_paid = AsyncMock()

                    response = await authenticated_client.post(
                        "/api/v1/payment/confirm",
                        json={
                            "paymentKey": "pk_test_123",
                            "orderId": "BIZ-1-BASIC-20260224-abc",
                            "amount": 10000,
                        },
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True

    async def test_confirm_invalid_order_id(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """유효하지 않은 주문 ID 형식"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True

            response = await authenticated_client.post(
                "/api/v1/payment/confirm",
                json={
                    "paymentKey": "pk_test",
                    "orderId": "BADFORMAT",
                    "amount": 10000,
                },
            )
            assert response.status_code == 400

    async def test_confirm_amount_mismatch(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """금액 불일치"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True
            mock_ps.get_plan_amount.return_value = 10000

            response = await authenticated_client.post(
                "/api/v1/payment/confirm",
                json={
                    "paymentKey": "pk_test",
                    "orderId": "BIZ-1-BASIC-20260224-abc",
                    "amount": 99999,
                },
            )
            assert response.status_code == 400


class TestCancelPaymentMocked:
    """결제 취소 (payment_service 모킹)"""

    async def test_cancel_success(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """결제 취소 성공"""
        # 결제 이력 생성
        payment = PaymentHistory(
            user_id=test_user.id,
            amount=10000,
            currency="KRW",
            status="paid",
            payment_method="card",
            transaction_id="pk_cancel_test",
            order_id="BIZ-1-BASIC-20260224-cancel",
            payment_type="subscription_create",
        )
        test_db.add(payment)
        await test_db.commit()

        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True
            mock_ps.cancel_payment = AsyncMock(return_value={"status": "CANCELED"})

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_ss.get_subscription = AsyncMock(return_value=None)

                response = await authenticated_client.post(
                    "/api/v1/payment/cancel",
                    json={
                        "paymentKey": "pk_cancel_test",
                        "cancelReason": "테스트 환불",
                    },
                )
                assert response.status_code == 200

    async def test_cancel_not_found(
        self, authenticated_client: AsyncClient, test_db: AsyncSession
    ):
        """결제 내역 없음"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True

            response = await authenticated_client.post(
                "/api/v1/payment/cancel",
                json={
                    "paymentKey": "pk_nonexistent",
                    "cancelReason": "존재하지 않는 결제",
                },
            )
            assert response.status_code == 404

    async def test_cancel_already_refunded(
        self, authenticated_client: AsyncClient, test_db: AsyncSession, test_user
    ):
        """이미 환불된 결제"""
        payment = PaymentHistory(
            user_id=test_user.id,
            amount=10000,
            currency="KRW",
            status="refunded",
            payment_method="card",
            transaction_id="pk_already_refunded",
            order_id="BIZ-1-BASIC-refunded",
            payment_type="subscription_create",
        )
        test_db.add(payment)
        await test_db.commit()

        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.is_configured.return_value = True

            response = await authenticated_client.post(
                "/api/v1/payment/cancel",
                json={
                    "paymentKey": "pk_already_refunded",
                    "cancelReason": "이미 환불됨",
                },
            )
            # PaymentAlreadyRefundedError
            assert response.status_code == 400


class TestChangePlanMocked:
    """플랜 변경 (구독 있는 상태, 모킹)"""

    async def test_change_to_free(
        self, authenticated_client: AsyncClient, test_subscription, test_db: AsyncSession
    ):
        """무료 플랜으로 변경 시도"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.get_plan_amount.side_effect = lambda p: {"free": 0, "basic": 10000, "pro": 30000}.get(p, 0)
            mock_ps.calculate_proration.return_value = 0

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_sub = MagicMock()
                mock_sub.plan_name = "basic"
                mock_sub.is_active = True
                mock_ss.get_subscription = AsyncMock(return_value=mock_sub)

                response = await authenticated_client.post(
                    "/api/v1/payment/subscription/change-plan",
                    json={"new_plan": "free"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["action"] == "cancel_required"

    async def test_upgrade_to_pro(
        self, authenticated_client: AsyncClient, test_subscription, test_db: AsyncSession
    ):
        """Pro로 업그레이드"""
        with patch("app.api.endpoints.payment.payment_service") as mock_ps:
            mock_ps.get_plan_amount.side_effect = lambda p: {"free": 0, "basic": 10000, "pro": 30000}.get(p, 0)
            mock_ps.calculate_proration.return_value = 15000

            with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
                mock_sub = MagicMock()
                mock_sub.plan_name = "basic"
                mock_sub.is_active = True
                mock_sub.end_date = datetime.utcnow() + timedelta(days=15)
                mock_ss.get_subscription = AsyncMock(return_value=mock_sub)

                response = await authenticated_client.post(
                    "/api/v1/payment/subscription/change-plan",
                    json={"new_plan": "pro"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["data"]["action"] == "payment_required"


class TestWebhookMocked:
    """웹훅 (결제 이력 있는 경우)"""

    async def test_webhook_payment_done(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """PAYMENT_DONE 웹훅 처리"""
        from app.db.models import User
        from app.core.security import get_password_hash

        user = User(
            email="webhook_user@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        payment = PaymentHistory(
            user_id=user.id,
            amount=10000,
            currency="KRW",
            status="pending",
            payment_method="card",
            transaction_id="pk_webhook_done",
            order_id="BIZ-webhook-done",
            payment_type="subscription_create",
        )
        test_db.add(payment)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/payment/webhook",
            json={
                "eventType": "PAYMENT_DONE",
                "data": {"paymentKey": "pk_webhook_done", "status": "DONE"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["processed"] is True

    async def test_webhook_payment_cancelled(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """PAYMENT_CANCELLED 웹훅 처리"""
        from app.db.models import User
        from app.core.security import get_password_hash

        user = User(
            email="webhook_cancel@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        payment = PaymentHistory(
            user_id=user.id,
            amount=10000,
            currency="KRW",
            status="paid",
            payment_method="card",
            transaction_id="pk_webhook_cancel",
            order_id="BIZ-webhook-cancel",
            payment_type="subscription_create",
        )
        test_db.add(payment)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/payment/webhook",
            json={
                "eventType": "PAYMENT_CANCELLED",
                "data": {"paymentKey": "pk_webhook_cancel", "status": "CANCELED"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["processed"] is True

    async def test_webhook_payment_failed(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """PAYMENT_FAILED 웹훅 처리"""
        from app.db.models import User
        from app.core.security import get_password_hash

        user = User(
            email="webhook_fail@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        payment = PaymentHistory(
            user_id=user.id,
            amount=10000,
            currency="KRW",
            status="paid",
            payment_method="card",
            transaction_id="pk_webhook_fail",
            order_id="BIZ-webhook-fail",
            payment_type="subscription_create",
        )
        test_db.add(payment)
        await test_db.commit()

        with patch("app.api.endpoints.payment.subscription_service") as mock_ss:
            mock_ss.handle_payment_failure = AsyncMock()

            response = await async_client.post(
                "/api/v1/payment/webhook",
                json={
                    "eventType": "PAYMENT_FAILED",
                    "data": {"paymentKey": "pk_webhook_fail", "status": "ABORTED"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["processed"] is True
