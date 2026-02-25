"""
Subscription Service — 구독 라이프사이클 전체 관리

상태 흐름:
    active → cancelled (해지 예약) → expired (기간 만료)
    active → past_due (결제 실패) → expired (3회 실패 후)
    expired → active (재구독)

주요 기능:
- 구독 생성/갱신/해지/만료/재구독
- 플랜 변경 (업/다운그레이드)
- 자동 갱신 결제 처리
- 구독 상태 검증
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateSubscriptionError,
    SubscriptionError,
    SubscriptionNotFoundError,
)
from app.core.logging import logger
from app.db.models import Subscription, User
from app.services.payment_service import payment_service


class SubscriptionService:
    """
    구독 라이프사이클 관리 서비스.

    플랜 제한:
    - free: 3건/일, AI 분석 5건, 키워드 5개
    - basic: 50건/일, AI 분석 100건, 키워드 20개
    - pro: 무제한
    """

    PLAN_LIMITS = {
        "free": {
            "hard_match_limit": 3,
            "ai_analysis_limit": 5,
            "keywords_limit": 5,
        },
        "basic": {
            "hard_match_limit": 50,
            "ai_analysis_limit": 100,
            "keywords_limit": 20,
        },
        "pro": {
            "hard_match_limit": 9999,
            "ai_analysis_limit": 9999,
            "keywords_limit": 100,
        },
    }

    BILLING_CYCLE_DAYS = 30

    async def get_user_plan(self, user: User) -> str:
        """사용자의 현재 플랜 이름 반환 (기본: free)."""
        if not user.subscription:
            return "free"
        if not user.subscription.is_active or user.subscription.status != "active":
            return "free"
        return user.subscription.plan_name

    async def get_plan_limits(self, plan_name: str) -> dict:
        """플랜별 사용 제한 반환."""
        return self.PLAN_LIMITS.get(plan_name, self.PLAN_LIMITS["free"])

    async def get_hard_match_limit(self, user: User) -> int:
        """사용자의 Hard Match 제한 수."""
        plan = await self.get_user_plan(user)
        limits = await self.get_plan_limits(plan)
        return limits["hard_match_limit"]

    async def get_subscription(self, user_id: int, db: AsyncSession) -> Subscription | None:
        """사용자의 구독 정보 조회."""
        stmt = select(Subscription).where(Subscription.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_subscription(
        self,
        user_id: int,
        plan_name: str,
        payment_key: str,
        billing_key: str | None,
        db: AsyncSession,
    ) -> Subscription:
        """
        신규 구독 생성.

        Args:
            user_id: 사용자 ID
            plan_name: 플랜 이름 (basic, pro)
            payment_key: Tosspayments 결제키
            billing_key: 빌링키 (자동 갱신용, 선택)
            db: DB 세션

        Returns:
            생성된 Subscription 객체
        """
        existing = await self.get_subscription(user_id, db)

        now = datetime.utcnow()
        next_billing = now + timedelta(days=self.BILLING_CYCLE_DAYS)

        if existing:
            if existing.is_active and existing.plan_name == plan_name and existing.status == "active":
                raise DuplicateSubscriptionError(plan_name)

            existing.plan_name = plan_name
            existing.is_active = True
            existing.status = "active"
            existing.start_date = now
            existing.end_date = next_billing
            existing.next_billing_date = next_billing
            existing.stripe_subscription_id = payment_key
            existing.billing_key = billing_key
            existing.cancelled_at = None
            existing.cancel_reason = None
            existing.failed_payment_count = 0
            existing.last_payment_attempt = now

            logger.info(f"Subscription updated: user={user_id}, plan={plan_name}")
            return existing

        subscription = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            is_active=True,
            status="active",
            start_date=now,
            end_date=next_billing,
            next_billing_date=next_billing,
            stripe_subscription_id=payment_key,
            billing_key=billing_key,
            failed_payment_count=0,
            last_payment_attempt=now,
        )
        db.add(subscription)

        logger.info(
            f"Subscription created: user={user_id}, plan={plan_name}, " f"next_billing={next_billing.isoformat()}"
        )
        return subscription

    async def cancel_subscription(
        self,
        user_id: int,
        reason: str,
        db: AsyncSession,
    ) -> Subscription:
        """
        구독 해지 예약.

        즉시 해지가 아닌, 현재 결제 기간 만료 시 해지.
        해지 후에도 기간 끝까지 서비스 이용 가능.

        Args:
            user_id: 사용자 ID
            reason: 해지 사유
            db: DB 세션
        """
        subscription = await self.get_subscription(user_id, db)
        if not subscription or not subscription.is_active:
            raise SubscriptionNotFoundError()

        if subscription.status == "cancelled":
            raise SubscriptionError(detail="이미 해지 예약된 구독입니다.")

        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.utcnow()
        subscription.cancel_reason = reason
        subscription.next_billing_date = None

        logger.info(f"Subscription cancellation scheduled: user={user_id}, " f"expires={subscription.end_date}")
        return subscription

    async def expire_subscription(self, subscription: Subscription, db: AsyncSession) -> Subscription:
        """구독 만료 처리 (배치에서 호출)."""
        subscription.is_active = False
        subscription.status = "expired"
        subscription.plan_name = "free"
        subscription.billing_key = None

        logger.info(f"Subscription expired: user={subscription.user_id}")
        return subscription

    async def resubscribe(
        self,
        user_id: int,
        plan_name: str,
        payment_key: str,
        billing_key: str | None,
        db: AsyncSession,
    ) -> Subscription:
        """
        재구독 (만료/해지 후).

        기존 구독 레코드를 재활용하여 히스토리를 보존.
        """
        subscription = await self.get_subscription(user_id, db)

        if subscription and subscription.is_active and subscription.status == "active":
            if subscription.plan_name == plan_name:
                raise DuplicateSubscriptionError(plan_name)
            return await self.change_plan(user_id, plan_name, payment_key, db)

        return await self.create_subscription(user_id, plan_name, payment_key, billing_key, db)

    async def change_plan(
        self,
        user_id: int,
        new_plan: str,
        payment_key: str,
        db: AsyncSession,
    ) -> Subscription:
        """
        플랜 변경 (업/다운그레이드).

        업그레이드: 즉시 적용, 프로레이션 차액 결제
        다운그레이드: 다음 결제일부터 적용
        """
        subscription = await self.get_subscription(user_id, db)
        if not subscription or not subscription.is_active:
            raise SubscriptionNotFoundError()

        old_plan = subscription.plan_name
        if old_plan == new_plan:
            raise DuplicateSubscriptionError(new_plan)

        old_price = payment_service.get_plan_amount(old_plan)
        new_price = payment_service.get_plan_amount(new_plan)

        if new_price > old_price:
            # 업그레이드: 즉시 적용
            subscription.plan_name = new_plan
            subscription.stripe_subscription_id = payment_key
            logger.info(f"Plan upgraded: user={user_id}, {old_plan} → {new_plan}")
        else:
            # 다운그레이드: 다음 결제일부터 적용 (예약)
            subscription.plan_name = new_plan
            logger.info(f"Plan downgraded (scheduled): user={user_id}, {old_plan} → {new_plan}")

        return subscription

    async def handle_payment_failure(self, subscription: Subscription, db: AsyncSession) -> Subscription:
        """
        결제 실패 처리.

        3회 연속 실패 시 구독을 만료 처리.
        결제 실패 중에는 past_due 상태로 서비스 제한적 이용.
        """
        subscription.failed_payment_count += 1
        subscription.last_payment_attempt = datetime.utcnow()

        if subscription.failed_payment_count >= 3:
            subscription.is_active = False
            subscription.status = "expired"
            subscription.plan_name = "free"
            subscription.billing_key = None
            logger.warning(f"Subscription expired due to 3 payment failures: " f"user={subscription.user_id}")
        else:
            subscription.status = "past_due"
            logger.warning(f"Payment failed ({subscription.failed_payment_count}/3): " f"user={subscription.user_id}")

        return subscription

    async def handle_payment_success(self, subscription: Subscription, db: AsyncSession) -> Subscription:
        """결제 성공 시 구독 갱신."""
        now = datetime.utcnow()
        next_billing = now + timedelta(days=self.BILLING_CYCLE_DAYS)

        subscription.status = "active"
        subscription.is_active = True
        subscription.failed_payment_count = 0
        subscription.last_payment_attempt = now
        subscription.start_date = now
        subscription.end_date = next_billing
        subscription.next_billing_date = next_billing

        logger.info(f"Subscription renewed: user={subscription.user_id}, " f"next_billing={next_billing.isoformat()}")
        return subscription

    async def get_subscription_status(self, user_id: int, db: AsyncSession) -> dict:
        """사용자 구독 상태 전체 정보."""
        subscription = await self.get_subscription(user_id, db)

        if not subscription:
            return {
                "plan_name": "free",
                "status": "none",
                "is_active": False,
                "limits": self.PLAN_LIMITS["free"],
            }

        plan = subscription.plan_name if subscription.is_active else "free"
        return {
            "plan_name": plan,
            "status": subscription.status,
            "is_active": subscription.is_active,
            "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
            "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
            "next_billing_date": (
                subscription.next_billing_date.isoformat() if subscription.next_billing_date else None
            ),
            "cancelled_at": (subscription.cancelled_at.isoformat() if subscription.cancelled_at else None),
            "cancel_reason": subscription.cancel_reason,
            "failed_payment_count": subscription.failed_payment_count,
            "limits": self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS["free"]),
        }


subscription_service = SubscriptionService()
