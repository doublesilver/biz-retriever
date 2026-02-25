"""
Payment API Endpoints — Tosspayments Enterprise Integration

결제 하드닝:
- 멱등성 키(Idempotency-Key) 기반 중복 결제 방지
- HMAC-SHA256 웹훅 서명 검증
- 서버 사이드 금액 검증 (클라이언트 변조 방지)
- 표준 ApiResponse envelope (ok/fail 헬퍼)
- 도메인 예외 사용 (HTTPException 대신 BizRetrieverError 계층)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import (
    BadRequestError,
    DuplicateSubscriptionError,
    NotFoundError,
    PaymentAlreadyRefundedError,
    PaymentNotConfiguredError,
    SubscriptionNotFoundError,
    WebhookVerificationError,
)
from app.core.logging import logger
from app.db.models import PaymentHistory, Subscription, User
from app.db.session import get_db
from app.schemas.response import ok, ok_paginated
from app.services.invoice_service import invoice_service
from app.services.payment_service import payment_service
from app.services.rate_limiter import limiter
from app.services.subscription_service import subscription_service

router = APIRouter()


# ============================================
# Request/Response Schemas
# ============================================


class PaymentCreateRequest(BaseModel):
    plan_name: str = Field(
        ..., pattern="^(basic|pro)$", description="구독 플랜 (basic 또는 pro)"
    )


class PaymentConfirmRequest(BaseModel):
    paymentKey: str = Field(..., min_length=1, description="Tosspayments 결제키")
    orderId: str = Field(..., min_length=1, description="주문 ID")
    amount: int = Field(..., gt=0, description="결제 금액 (KRW)")


class PaymentCancelRequest(BaseModel):
    paymentKey: str = Field(..., min_length=1)
    cancelReason: str = Field(..., min_length=1, max_length=200)


class SubscriptionCancelRequest(BaseModel):
    reason: str = Field(
        ..., min_length=1, max_length=500, description="해지 사유"
    )


class PlanChangeRequest(BaseModel):
    new_plan: str = Field(
        ..., pattern="^(free|basic|pro)$", description="변경할 플랜"
    )


# ============================================
# 결제 생성 및 승인
# ============================================


@router.post("/create")
@limiter.limit("10/minute")
async def create_payment(
    http_request: Request,
    request: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    결제 요청 생성 — Tosspayments 프론트엔드 SDK용 데이터 반환.

    서버에서 금액을 결정하여 클라이언트 변조를 방지.
    """
    if not payment_service.is_configured():
        raise PaymentNotConfiguredError()

    # 이미 같은 플랜 구독 중인지 확인
    subscription = await subscription_service.get_subscription(
        current_user.id, db
    )
    if (
        subscription
        and subscription.plan_name == request.plan_name
        and subscription.is_active
        and subscription.status == "active"
    ):
        raise DuplicateSubscriptionError(request.plan_name)

    # 서버에서 금액 결정 (클라이언트가 보낸 금액 사용 안함)
    amount = payment_service.get_plan_amount(request.plan_name)
    if amount == 0:
        raise BadRequestError("무료 플랜은 결제가 필요하지 않습니다.")

    order_id = payment_service.generate_order_id(
        current_user.id, request.plan_name
    )

    payment_data = await payment_service.create_payment(
        amount=amount,
        order_id=order_id,
        order_name=f"Biz-Retriever {request.plan_name.upper()} 플랜",
        customer_email=current_user.email,
        customer_name=current_user.email.split("@")[0],
    )

    logger.info(
        f"Payment created: user={current_user.id}, "
        f"plan={request.plan_name}, order_id={order_id}"
    )

    return ok(payment_data)


@router.post("/confirm")
@limiter.limit("10/minute")
async def confirm_payment(
    http_request: Request,
    request: PaymentConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    결제 승인 — Tosspayments 결제 완료 후 호출.

    보안 포인트:
    1. 서버에서 금액 재검증 (orderId에서 플랜 추출 후 가격 비교)
    2. 멱등성 키로 중복 승인 방지
    3. 인보이스 자동 생성
    """
    if not payment_service.is_configured():
        raise PaymentNotConfiguredError()

    # orderId에서 플랜 추출 (format: BIZ-{userId}-{PLAN}-{ts}-{uuid})
    order_parts = request.orderId.split("-")
    if len(order_parts) < 3:
        raise BadRequestError("유효하지 않은 주문 ID 형식입니다.")

    plan_name = order_parts[2].lower()
    if plan_name not in ("basic", "pro"):
        raise BadRequestError("유효하지 않은 플랜입니다.")

    # 서버 사이드 금액 검증 — 클라이언트 변조 방지
    expected_amount = payment_service.get_plan_amount(plan_name)
    if request.amount != expected_amount:
        logger.warning(
            f"Amount mismatch: user={current_user.id}, "
            f"expected={expected_amount}, received={request.amount}"
        )
        raise BadRequestError("결제 금액이 일치하지 않습니다.")

    # 멱등성 키 생성 (중복 결제 방지)
    idempotency_key = payment_service.generate_idempotency_key()

    # 중복 결제 체크 (같은 orderId)
    stmt = select(PaymentHistory).where(
        PaymentHistory.order_id == request.orderId,
        PaymentHistory.status == "paid",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise BadRequestError("이미 처리된 주문입니다.")

    # Tosspayments API 결제 승인 (지수 백오프 재시도 포함)
    await payment_service.confirm_payment(
        payment_key=request.paymentKey,
        order_id=request.orderId,
        amount=request.amount,
        idempotency_key=idempotency_key,
    )

    # 구독 생성/갱신
    subscription = await subscription_service.create_subscription(
        user_id=current_user.id,
        plan_name=plan_name,
        payment_key=request.paymentKey,
        billing_key=None,
        db=db,
    )

    # 결제 이력 기록
    payment_history = PaymentHistory(
        user_id=current_user.id,
        amount=request.amount,
        currency="KRW",
        status="paid",
        payment_method="card",
        transaction_id=request.paymentKey,
        idempotency_key=idempotency_key,
        order_id=request.orderId,
        payment_type="subscription_create",
    )
    db.add(payment_history)

    # 인보이스 생성
    invoice = await invoice_service.create_invoice(
        subscription=subscription,
        amount=request.amount,
        plan_name=plan_name,
        payment_key=request.paymentKey,
        description=f"{plan_name.upper()} 플랜 신규 구독",
        db=db,
    )
    await invoice_service.mark_paid(invoice, request.paymentKey)

    await db.commit()

    logger.info(
        f"Payment confirmed: user={current_user.id}, plan={plan_name}, "
        f"amount={request.amount}원, invoice={invoice.invoice_number}"
    )

    return ok({
        "plan_name": plan_name,
        "next_billing_date": subscription.next_billing_date.isoformat(),
        "invoice_number": invoice.invoice_number,
        "message": f"{plan_name.upper()} 플랜 구독이 활성화되었습니다!",
    })


# ============================================
# 결제 취소/환불
# ============================================


@router.post("/cancel")
@limiter.limit("5/minute")
async def cancel_payment(
    http_request: Request,
    request: PaymentCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """결제 취소/환불."""
    if not payment_service.is_configured():
        raise PaymentNotConfiguredError()

    # 결제 이력 조회
    stmt = select(PaymentHistory).where(
        PaymentHistory.user_id == current_user.id,
        PaymentHistory.transaction_id == request.paymentKey,
    )
    result = await db.execute(stmt)
    payment_record = result.scalar_one_or_none()

    if not payment_record:
        raise NotFoundError("결제 내역")

    if payment_record.status == "refunded":
        raise PaymentAlreadyRefundedError()

    # Tosspayments API 취소 요청
    await payment_service.cancel_payment(
        payment_key=request.paymentKey,
        cancel_reason=request.cancelReason,
    )

    # 상태 업데이트
    payment_record.status = "refunded"

    # 구독 다운그레이드
    subscription = await subscription_service.get_subscription(
        current_user.id, db
    )
    if subscription:
        subscription.plan_name = "free"
        subscription.is_active = True
        subscription.status = "active"
        subscription.next_billing_date = None
        subscription.billing_key = None

    await db.commit()

    logger.info(
        f"Payment cancelled: user={current_user.id}, "
        f"payment_key={request.paymentKey}"
    )

    return ok({"message": "결제가 취소되고 환불 처리되었습니다."})


# ============================================
# 구독 관리
# ============================================


@router.get("/subscription")
@limiter.limit("30/minute")
async def get_subscription_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 구독 상태 조회."""
    status = await subscription_service.get_subscription_status(
        current_user.id, db
    )
    return ok(status)


@router.post("/subscription/cancel")
@limiter.limit("5/minute")
async def cancel_subscription(
    http_request: Request,
    request: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    구독 해지 예약.

    즉시 해지가 아닌, 현재 결제 기간 만료 후 해지.
    기간 끝까지 서비스 이용 가능.
    """
    subscription = await subscription_service.cancel_subscription(
        user_id=current_user.id,
        reason=request.reason,
        db=db,
    )
    await db.commit()

    return ok({
        "message": "구독 해지가 예약되었습니다. 기간 만료까지 서비스를 이용하실 수 있습니다.",
        "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
        "status": subscription.status,
    })


@router.post("/subscription/change-plan")
@limiter.limit("5/minute")
async def change_plan(
    http_request: Request,
    request: PlanChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    플랜 변경 — 업그레이드/다운그레이드.

    업그레이드: 프로레이션 차액 결제 필요 (클라이언트에서 별도 결제 진행).
    다운그레이드: 다음 결제일부터 적용.
    """
    subscription = await subscription_service.get_subscription(
        current_user.id, db
    )
    if not subscription or not subscription.is_active:
        raise SubscriptionNotFoundError()

    old_plan = subscription.plan_name
    new_plan = request.new_plan

    if new_plan == "free":
        return ok({
            "action": "cancel_required",
            "message": "무료 플랜으로 전환하려면 구독을 해지해 주세요.",
        })

    old_price = payment_service.get_plan_amount(old_plan)
    new_price = payment_service.get_plan_amount(new_plan)

    # 프로레이션 계산
    days_remaining = 0
    if subscription.end_date:
        delta = subscription.end_date - datetime.utcnow()
        days_remaining = max(0, delta.days)

    proration = payment_service.calculate_proration(
        old_plan, new_plan, days_remaining
    )

    if new_price > old_price:
        # 업그레이드: 추가 결제 필요
        return ok({
            "action": "payment_required",
            "old_plan": old_plan,
            "new_plan": new_plan,
            "proration_amount": proration,
            "message": f"{proration:,}원 추가 결제가 필요합니다.",
        })
    else:
        # 다운그레이드: 다음 결제일부터 적용
        subscription = await subscription_service.change_plan(
            user_id=current_user.id,
            new_plan=new_plan,
            payment_key=subscription.stripe_subscription_id or "",
            db=db,
        )
        await db.commit()

        return ok({
            "action": "scheduled",
            "old_plan": old_plan,
            "new_plan": new_plan,
            "effective_date": (
                subscription.next_billing_date.isoformat()
                if subscription.next_billing_date
                else None
            ),
            "message": f"다음 결제일부터 {new_plan.upper()} 플랜으로 변경됩니다.",
        })


# ============================================
# 결제 이력 및 인보이스
# ============================================


@router.get("/history")
@limiter.limit("30/minute")
async def get_payment_history(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """결제 이력 조회 (페이지네이션)."""
    stmt = (
        select(PaymentHistory)
        .where(PaymentHistory.user_id == current_user.id)
        .order_by(desc(PaymentHistory.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()

    count_stmt = select(func.count(PaymentHistory.id)).where(
        PaymentHistory.user_id == current_user.id
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    items = [
        {
            "id": p.id,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,
            "payment_method": p.payment_method,
            "transaction_id": p.transaction_id,
            "order_id": p.order_id,
            "payment_type": p.payment_type,
            "created_at": p.created_at.isoformat(),
        }
        for p in payments
    ]

    return ok_paginated(items, total=total, skip=skip, limit=limit)


@router.get("/invoices")
@limiter.limit("30/minute")
async def get_invoices(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """인보이스 목록 조회."""
    invoices = await invoice_service.get_user_invoices(
        current_user.id, db, skip=skip, limit=limit
    )
    total = await invoice_service.get_user_invoice_count(
        current_user.id, db
    )

    items = [
        {
            "invoice_number": inv.invoice_number,
            "amount": inv.amount,
            "subtotal": inv.subtotal,
            "tax_amount": inv.tax_amount,
            "proration_amount": inv.proration_amount,
            "currency": inv.currency,
            "status": inv.status,
            "plan_name": inv.plan_name,
            "billing_period_start": (
                inv.billing_period_start.isoformat()
                if inv.billing_period_start
                else None
            ),
            "billing_period_end": (
                inv.billing_period_end.isoformat()
                if inv.billing_period_end
                else None
            ),
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "description": inv.description,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invoices
    ]

    return ok_paginated(items, total=total, skip=skip, limit=limit)


@router.get("/invoices/{invoice_number}")
@limiter.limit("30/minute")
async def get_invoice_detail(
    invoice_number: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """인보이스 상세 조회."""
    invoice = await invoice_service.get_invoice_by_number(
        invoice_number, db
    )

    # 본인의 인보이스만 조회 가능
    if invoice.user_id != current_user.id:
        raise NotFoundError("인보이스", invoice_number)

    return ok({
        "invoice_number": invoice.invoice_number,
        "amount": invoice.amount,
        "subtotal": invoice.subtotal,
        "tax_amount": invoice.tax_amount,
        "proration_amount": invoice.proration_amount,
        "currency": invoice.currency,
        "status": invoice.status,
        "plan_name": invoice.plan_name,
        "billing_period_start": (
            invoice.billing_period_start.isoformat()
            if invoice.billing_period_start
            else None
        ),
        "billing_period_end": (
            invoice.billing_period_end.isoformat()
            if invoice.billing_period_end
            else None
        ),
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "payment_key": invoice.payment_key,
        "description": invoice.description,
        "created_at": invoice.created_at.isoformat(),
    })


# ============================================
# 웹훅
# ============================================


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Tosspayments 웹훅 핸들러.

    보안:
    - HMAC-SHA256 서명 검증 (위변조 방지)
    - 내부 에러 상세를 외부에 노출하지 않음 (A03)
    """
    # 원본 body 읽기 (서명 검증용)
    body = await request.body()

    # HMAC 서명 검증
    signature = request.headers.get("Toss-Signature", "")
    if not payment_service.verify_webhook_signature(body, signature):
        logger.warning(
            "Webhook signature verification failed: ip=%s",
            request.client.host if request.client else "unknown",
        )
        raise WebhookVerificationError()

    try:
        payload = await request.json()
    except Exception:
        raise BadRequestError("유효하지 않은 웹훅 페이로드입니다.")

    event_type = payload.get("eventType")
    data = payload.get("data", {})
    payment_key = data.get("paymentKey")
    status = data.get("status")

    logger.info(
        "Webhook received: event=%s, payment_key=%s, status=%s",
        event_type, payment_key, status,
    )

    if not payment_key:
        logger.warning("Webhook missing payment_key")
        return ok({"processed": False, "reason": "missing_payment_key"})

    # 결제 이력 조회
    stmt = select(PaymentHistory).where(
        PaymentHistory.transaction_id == payment_key
    )
    result = await db.execute(stmt)
    payment_record = result.scalar_one_or_none()

    if not payment_record:
        logger.warning("Payment not found for webhook: %s", payment_key)
        return ok({"processed": False, "reason": "payment_not_found"})

    # 이벤트 타입별 처리
    if event_type == "PAYMENT_DONE":
        payment_record.status = "paid"

    elif event_type == "PAYMENT_FAILED":
        payment_record.status = "failed"

        # 구독 결제 실패 처리
        if payment_record.user_id:
            sub_stmt = select(Subscription).where(
                Subscription.user_id == payment_record.user_id
            )
            sub_result = await db.execute(sub_stmt)
            subscription = sub_result.scalar_one_or_none()
            if subscription:
                await subscription_service.handle_payment_failure(
                    subscription, db
                )

    elif event_type == "PAYMENT_CANCELLED":
        payment_record.status = "refunded"

        # 구독 다운그레이드
        if payment_record.user_id:
            sub_stmt = select(Subscription).where(
                Subscription.user_id == payment_record.user_id
            )
            sub_result = await db.execute(sub_stmt)
            subscription = sub_result.scalar_one_or_none()
            if subscription:
                subscription.plan_name = "free"
                subscription.next_billing_date = None

    await db.commit()

    logger.info(
        "Webhook processed: payment_key=%s, event=%s",
        payment_key, event_type,
    )

    return ok({"processed": True, "event_type": event_type})


# ============================================
# 플랜 정보
# ============================================


@router.get("/plans")
@limiter.limit("30/minute")
async def get_plans(request: Request):
    """구독 플랜 목록 조회."""
    plans = [
        {
            "name": "free",
            "price": 0,
            "description": "무료 체험",
            "features": [
                "Hard Match 3건/일",
                "AI 분석 5건/일",
                "키워드 5개",
            ],
        },
        {
            "name": "basic",
            "price": 10000,
            "description": "기본 플랜",
            "features": [
                "Hard Match 50건/일",
                "AI 분석 100건/일",
                "키워드 20개",
                "이메일 알림",
            ],
        },
        {
            "name": "pro",
            "price": 30000,
            "description": "프로 플랜",
            "features": [
                "Hard Match 무제한",
                "AI 분석 무제한",
                "키워드 100개",
                "이메일 + Slack 알림",
                "우선 지원",
            ],
        },
    ]
    return ok(plans)
