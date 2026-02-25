"""
SubscriptionService 단위 테스트
- 플랜 제한 조회
- 구독 생성/해지/만료/재구독/플랜변경
- 결제 실패/성공 처리
- 구독 상태 조회
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import (
    DuplicateSubscriptionError,
    SubscriptionError,
    SubscriptionNotFoundError,
)
from app.services.subscription_service import SubscriptionService


def make_user(plan_name="free", is_active=True, status="active"):
    """Mock User 생성"""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    if plan_name == "free" and not is_active:
        user.subscription = None
    else:
        sub = MagicMock()
        sub.plan_name = plan_name
        sub.is_active = is_active
        sub.status = status
        user.subscription = sub
    return user


def make_subscription(**overrides):
    """Mock Subscription 생성"""
    sub = MagicMock()
    sub.user_id = overrides.get("user_id", 1)
    sub.plan_name = overrides.get("plan_name", "basic")
    sub.is_active = overrides.get("is_active", True)
    sub.status = overrides.get("status", "active")
    sub.start_date = overrides.get("start_date", datetime.utcnow())
    sub.end_date = overrides.get("end_date", datetime.utcnow() + timedelta(days=30))
    sub.next_billing_date = overrides.get("next_billing_date", datetime.utcnow() + timedelta(days=30))
    sub.billing_key = overrides.get("billing_key", None)
    sub.cancelled_at = overrides.get("cancelled_at", None)
    sub.cancel_reason = overrides.get("cancel_reason", None)
    sub.failed_payment_count = overrides.get("failed_payment_count", 0)
    sub.last_payment_attempt = overrides.get("last_payment_attempt", None)
    sub.stripe_subscription_id = overrides.get("stripe_subscription_id", None)
    return sub


class TestGetUserPlan:
    """사용자 플랜 조회 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_no_subscription_returns_free(self):
        user = make_user()
        user.subscription = None
        result = await self.service.get_user_plan(user)
        assert result == "free"

    async def test_inactive_subscription_returns_free(self):
        user = MagicMock()
        user.subscription = MagicMock()
        user.subscription.is_active = False
        user.subscription.status = "expired"
        user.subscription.plan_name = "basic"
        result = await self.service.get_user_plan(user)
        assert result == "free"

    async def test_cancelled_subscription_returns_free(self):
        user = MagicMock()
        user.subscription = MagicMock()
        user.subscription.is_active = True
        user.subscription.status = "cancelled"
        user.subscription.plan_name = "basic"
        result = await self.service.get_user_plan(user)
        assert result == "free"

    async def test_active_basic_returns_basic(self):
        user = make_user(plan_name="basic")
        result = await self.service.get_user_plan(user)
        assert result == "basic"

    async def test_active_pro_returns_pro(self):
        user = make_user(plan_name="pro")
        result = await self.service.get_user_plan(user)
        assert result == "pro"


class TestGetPlanLimits:
    """플랜 제한 조회 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_free_limits(self):
        limits = await self.service.get_plan_limits("free")
        assert limits["hard_match_limit"] == 3
        assert limits["ai_analysis_limit"] == 5
        assert limits["keywords_limit"] == 5

    async def test_basic_limits(self):
        limits = await self.service.get_plan_limits("basic")
        assert limits["hard_match_limit"] == 50
        assert limits["ai_analysis_limit"] == 100
        assert limits["keywords_limit"] == 20

    async def test_pro_limits(self):
        limits = await self.service.get_plan_limits("pro")
        assert limits["hard_match_limit"] == 9999

    async def test_unknown_plan_returns_free(self):
        limits = await self.service.get_plan_limits("enterprise")
        assert limits == self.service.PLAN_LIMITS["free"]


class TestGetHardMatchLimit:
    """Hard Match 제한 조회"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_free_user_limit(self):
        user = make_user()
        user.subscription = None
        limit = await self.service.get_hard_match_limit(user)
        assert limit == 3

    async def test_basic_user_limit(self):
        user = make_user(plan_name="basic")
        limit = await self.service.get_hard_match_limit(user)
        assert limit == 50


class TestCreateSubscription:
    """구독 생성 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_create_new_subscription(self):
        """구독이 없는 사용자에게 새 구독 생성"""
        db = AsyncMock()
        db.add = MagicMock()
        self.service.get_subscription = AsyncMock(return_value=None)
        result = await self.service.create_subscription(
            user_id=1, plan_name="basic", payment_key="pk_test", billing_key=None, db=db
        )
        assert result.plan_name == "basic"
        assert result.is_active is True
        db.add.assert_called_once()

    async def test_create_updates_existing_inactive(self):
        """비활성 구독이 있으면 업데이트"""
        db = AsyncMock()
        sub = make_subscription(plan_name="free", is_active=False, status="expired")
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.create_subscription(
            user_id=1, plan_name="basic", payment_key="pk_test", billing_key=None, db=db
        )
        assert result.plan_name == "basic"
        assert result.is_active is True
        assert result.status == "active"

    async def test_create_duplicate_raises(self):
        """같은 활성 플랜으로 생성 시도 시 DuplicateSubscriptionError"""
        db = AsyncMock()
        sub = make_subscription(plan_name="basic", is_active=True, status="active")
        self.service.get_subscription = AsyncMock(return_value=sub)
        with pytest.raises(DuplicateSubscriptionError):
            await self.service.create_subscription(
                user_id=1, plan_name="basic", payment_key="pk_test", billing_key=None, db=db
            )


class TestResubscribe:
    """재구독 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    @patch("app.services.subscription_service.payment_service")
    async def test_resubscribe_active_same_plan_raises(self, mock_pay):
        """활성 구독 + 같은 플랜 재구독 시도"""
        db = AsyncMock()
        sub = make_subscription(plan_name="basic", is_active=True, status="active")
        self.service.get_subscription = AsyncMock(return_value=sub)
        with pytest.raises(DuplicateSubscriptionError):
            await self.service.resubscribe(1, "basic", "pk_test", None, db)

    @patch("app.services.subscription_service.payment_service")
    async def test_resubscribe_active_different_plan(self, mock_pay):
        """활성 구독 + 다른 플랜 → change_plan"""
        mock_pay.get_plan_amount.side_effect = lambda p: {"basic": 10000, "pro": 30000}[p]
        db = AsyncMock()
        sub = make_subscription(plan_name="basic", is_active=True, status="active")
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.resubscribe(1, "pro", "pk_test", None, db)
        assert result.plan_name == "pro"

    async def test_resubscribe_no_subscription(self):
        """구독 없는 사용자 재구독 → 새 구독 생성"""
        db = AsyncMock()
        db.add = MagicMock()
        self.service.get_subscription = AsyncMock(return_value=None)
        result = await self.service.resubscribe(1, "basic", "pk_test", None, db)
        assert result.plan_name == "basic"


class TestCancelSubscription:
    """구독 해지 예약 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_cancel_no_subscription_raises(self):
        db = AsyncMock()
        self.service.get_subscription = AsyncMock(return_value=None)
        with pytest.raises(SubscriptionNotFoundError):
            await self.service.cancel_subscription(1, "해지 사유", db)

    async def test_cancel_inactive_raises(self):
        db = AsyncMock()
        sub = make_subscription(is_active=False)
        self.service.get_subscription = AsyncMock(return_value=sub)
        with pytest.raises(SubscriptionNotFoundError):
            await self.service.cancel_subscription(1, "해지", db)

    async def test_cancel_already_cancelled_raises(self):
        db = AsyncMock()
        sub = make_subscription(status="cancelled")
        self.service.get_subscription = AsyncMock(return_value=sub)
        with pytest.raises(SubscriptionError):
            await self.service.cancel_subscription(1, "해지", db)

    async def test_cancel_success(self):
        db = AsyncMock()
        sub = make_subscription(status="active")
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.cancel_subscription(1, "가격 부담", db)
        assert result.status == "cancelled"
        assert result.cancelled_at is not None
        assert result.cancel_reason == "가격 부담"
        assert result.next_billing_date is None


class TestExpireSubscription:
    """구독 만료 처리 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_expire(self):
        db = AsyncMock()
        sub = make_subscription()
        result = await self.service.expire_subscription(sub, db)
        assert result.is_active is False
        assert result.status == "expired"
        assert result.plan_name == "free"
        assert result.billing_key is None


class TestHandlePaymentFailure:
    """결제 실패 처리 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_first_failure(self):
        db = AsyncMock()
        sub = make_subscription(failed_payment_count=0)
        result = await self.service.handle_payment_failure(sub, db)
        assert result.failed_payment_count == 1
        assert result.status == "past_due"
        assert result.is_active is True  # 아직 활성

    async def test_second_failure(self):
        db = AsyncMock()
        sub = make_subscription(failed_payment_count=1)
        result = await self.service.handle_payment_failure(sub, db)
        assert result.failed_payment_count == 2
        assert result.status == "past_due"

    async def test_third_failure_expires(self):
        db = AsyncMock()
        sub = make_subscription(failed_payment_count=2)
        result = await self.service.handle_payment_failure(sub, db)
        assert result.failed_payment_count == 3
        assert result.is_active is False
        assert result.status == "expired"
        assert result.plan_name == "free"
        assert result.billing_key is None


class TestHandlePaymentSuccess:
    """결제 성공 처리 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_success_renews(self):
        db = AsyncMock()
        sub = make_subscription(failed_payment_count=2, status="past_due")
        result = await self.service.handle_payment_success(sub, db)
        assert result.status == "active"
        assert result.is_active is True
        assert result.failed_payment_count == 0
        assert result.next_billing_date is not None


class TestChangePlan:
    """플랜 변경 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    @patch("app.services.subscription_service.payment_service")
    async def test_change_no_subscription_raises(self, mock_pay):
        db = AsyncMock()
        self.service.get_subscription = AsyncMock(return_value=None)
        with pytest.raises(SubscriptionNotFoundError):
            await self.service.change_plan(1, "pro", "pay_key", db)

    @patch("app.services.subscription_service.payment_service")
    async def test_change_same_plan_raises(self, mock_pay):
        db = AsyncMock()
        sub = make_subscription(plan_name="basic")
        self.service.get_subscription = AsyncMock(return_value=sub)
        with pytest.raises(DuplicateSubscriptionError):
            await self.service.change_plan(1, "basic", "pay_key", db)

    @patch("app.services.subscription_service.payment_service")
    async def test_upgrade(self, mock_pay):
        mock_pay.get_plan_amount.side_effect = lambda p: {"basic": 10000, "pro": 30000}[p]
        db = AsyncMock()
        sub = make_subscription(plan_name="basic")
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.change_plan(1, "pro", "pay_key", db)
        assert result.plan_name == "pro"

    @patch("app.services.subscription_service.payment_service")
    async def test_downgrade(self, mock_pay):
        mock_pay.get_plan_amount.side_effect = lambda p: {"basic": 10000, "pro": 30000}[p]
        db = AsyncMock()
        sub = make_subscription(plan_name="pro")
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.change_plan(1, "basic", "pay_key", db)
        assert result.plan_name == "basic"


class TestGetSubscriptionStatus:
    """구독 상태 조회 테스트"""

    def setup_method(self):
        self.service = SubscriptionService()

    async def test_no_subscription(self):
        db = AsyncMock()
        self.service.get_subscription = AsyncMock(return_value=None)
        result = await self.service.get_subscription_status(1, db)
        assert result["plan_name"] == "free"
        assert result["status"] == "none"
        assert result["is_active"] is False

    async def test_active_subscription(self):
        db = AsyncMock()
        sub = make_subscription(
            plan_name="basic",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            next_billing_date=datetime(2026, 1, 31),
        )
        self.service.get_subscription = AsyncMock(return_value=sub)
        result = await self.service.get_subscription_status(1, db)
        assert result["plan_name"] == "basic"
        assert result["is_active"] is True
        assert result["start_date"] is not None
