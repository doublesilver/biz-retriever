"""
Payment API Endpoints
Phase 3: Tosspayments integration for subscription billing
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import logger
from app.db.models import PaymentHistory, Subscription, User
from app.db.session import get_db
from app.services.payment_service import payment_service

router = APIRouter()


# Schemas
class PaymentCreateRequest(BaseModel):
    plan_name: str  # "basic" or "pro"


class PaymentCreateResponse(BaseModel):
    client_key: str
    amount: int
    orderId: str
    orderName: str
    customerEmail: str
    customerName: str
    successUrl: str
    failUrl: str


class PaymentConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int


class PaymentConfirmResponse(BaseModel):
    success: bool
    message: str
    plan_name: str
    next_billing_date: str


class PaymentCancelRequest(BaseModel):
    paymentKey: str
    cancelReason: str


class PaymentHistoryResponse(BaseModel):
    id: int
    amount: float
    currency: str
    status: str
    payment_method: str
    transaction_id: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(
    request: PaymentCreateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Create a payment request for plan upgrade

    Returns payment data for Tosspayments frontend SDK
    """
    if not payment_service.is_configured():
        raise HTTPException(status_code=503, detail="결제 시스템이 설정되지 않았습니다. 관리자에게 문의하세요.")

    # Validate plan name
    if request.plan_name not in ["basic", "pro"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 플랜입니다. 'basic' 또는 'pro'를 선택하세요.")

    # Check if already on this plan
    stmt = select(Subscription).where(Subscription.user_id == current_user.id)
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription and subscription.plan_name == request.plan_name and subscription.is_active:
        raise HTTPException(status_code=400, detail=f"이미 {request.plan_name.upper()} 플랜을 사용 중입니다.")

    # Get plan amount
    amount = payment_service.get_plan_amount(request.plan_name)

    if amount == 0:
        raise HTTPException(status_code=400, detail="무료 플랜은 결제가 필요하지 않습니다.")

    # Generate order ID
    order_id = payment_service.generate_order_id(current_user.id, request.plan_name)

    # Create payment data for frontend
    try:
        payment_data = await payment_service.create_payment(
            amount=amount,
            order_id=order_id,
            order_name=f"Biz-Retriever {request.plan_name.upper()} 플랜",
            customer_email=current_user.email,
            customer_name=current_user.email.split("@")[0],  # Use email prefix as name
        )

        logger.info(f"Payment created: user={current_user.id}, plan={request.plan_name}, order_id={order_id}")

        return PaymentCreateResponse(**payment_data)

    except Exception as e:
        logger.error(f"Failed to create payment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"결제 생성 실패: {str(e)}")


@router.post("/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    request: PaymentConfirmRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Confirm payment after user completes payment on Tosspayments UI

    This endpoint is called from frontend after successful payment
    """
    if not payment_service.is_configured():
        raise HTTPException(status_code=503, detail="결제 시스템이 설정되지 않았습니다.")

    try:
        # Confirm payment with Tosspayments API
        confirmation_result = await payment_service.confirm_payment(
            payment_key=request.paymentKey, order_id=request.orderId, amount=request.amount
        )

        # Extract plan name from order_id (format: BIZ-{user_id}-{PLAN}-{timestamp})
        order_parts = request.orderId.split("-")
        if len(order_parts) < 3:
            raise ValueError("Invalid order ID format")

        plan_name = order_parts[2].lower()  # BASIC or PRO -> basic or pro

        # Update or create subscription
        stmt = select(Subscription).where(Subscription.user_id == current_user.id)
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()

        next_billing_date = datetime.utcnow() + timedelta(days=30)  # Monthly billing

        if subscription:
            # Update existing subscription
            subscription.plan_name = plan_name
            subscription.is_active = True
            subscription.start_date = datetime.utcnow()
            subscription.next_billing_date = next_billing_date
            subscription.stripe_subscription_id = request.paymentKey  # Store payment key
        else:
            # Create new subscription
            subscription = Subscription(
                user_id=current_user.id,
                plan_name=plan_name,
                is_active=True,
                start_date=datetime.utcnow(),
                next_billing_date=next_billing_date,
                stripe_subscription_id=request.paymentKey,
            )
            db.add(subscription)

        # Record payment in history
        payment_history = PaymentHistory(
            user_id=current_user.id,
            amount=request.amount,
            currency="KRW",
            status="paid",
            payment_method="card",
            transaction_id=request.paymentKey,
        )
        db.add(payment_history)

        await db.commit()

        logger.info(f"Payment confirmed: user={current_user.id}, plan={plan_name}, amount={request.amount}원")

        return PaymentConfirmResponse(
            success=True,
            message=f"{plan_name.upper()} 플랜 구독이 활성화되었습니다!",
            plan_name=plan_name,
            next_billing_date=next_billing_date.isoformat(),
        )

    except Exception as e:
        logger.error(f"Payment confirmation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"결제 확인 실패: {str(e)}")


@router.post("/cancel")
async def cancel_payment(
    request: PaymentCancelRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Cancel/refund a payment
    """
    if not payment_service.is_configured():
        raise HTTPException(status_code=503, detail="결제 시스템이 설정되지 않았습니다.")

    try:
        # Find payment in history
        stmt = select(PaymentHistory).where(
            PaymentHistory.user_id == current_user.id, PaymentHistory.transaction_id == request.paymentKey
        )
        result = await db.execute(stmt)
        payment_record = result.scalar_one_or_none()

        if not payment_record:
            raise HTTPException(status_code=404, detail="결제 내역을 찾을 수 없습니다.")

        if payment_record.status == "refunded":
            raise HTTPException(status_code=400, detail="이미 환불된 결제입니다.")

        # Cancel payment with Tosspayments
        cancel_result = await payment_service.cancel_payment(
            payment_key=request.paymentKey, cancel_reason=request.cancelReason
        )

        # Update payment status
        payment_record.status = "refunded"

        # Downgrade to free plan
        stmt = select(Subscription).where(Subscription.user_id == current_user.id)
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.plan_name = "free"
            subscription.is_active = True
            subscription.next_billing_date = None

        await db.commit()

        logger.info(f"Payment cancelled: user={current_user.id}, payment_key={request.paymentKey}")

        return {"success": True, "message": "결제가 취소되고 환불 처리되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payment cancellation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"결제 취소 실패: {str(e)}")


@router.get("/history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get user's payment history
    """
    stmt = (
        select(PaymentHistory)
        .where(PaymentHistory.user_id == current_user.id)
        .order_by(desc(PaymentHistory.created_at))
    )

    result = await db.execute(stmt)
    payments = result.scalars().all()

    return [PaymentHistoryResponse.from_orm(p) for p in payments]


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook handler for Tosspayments notifications

    Tosspayments sends webhooks for payment status changes
    """
    try:
        # Parse webhook payload
        payload = await request.json()

        logger.info(f"Received payment webhook: {payload}")

        # Extract data from webhook
        event_type = payload.get("eventType")
        payment_key = payload.get("data", {}).get("paymentKey")
        order_id = payload.get("data", {}).get("orderId")
        status = payload.get("data", {}).get("status")

        if not payment_key:
            logger.warning("Webhook missing payment_key")
            return {"success": False, "message": "Missing payment_key"}

        # Find payment in history
        stmt = select(PaymentHistory).where(PaymentHistory.transaction_id == payment_key)
        result = await db.execute(stmt)
        payment_record = result.scalar_one_or_none()

        if not payment_record:
            logger.warning(f"Payment not found for webhook: {payment_key}")
            return {"success": False, "message": "Payment not found"}

        # Update payment status based on webhook event
        if event_type == "PAYMENT_DONE":
            payment_record.status = "paid"
        elif event_type == "PAYMENT_FAILED":
            payment_record.status = "failed"
        elif event_type == "PAYMENT_CANCELLED":
            payment_record.status = "refunded"

            # Downgrade subscription if payment was cancelled
            stmt = select(Subscription).where(Subscription.user_id == payment_record.user_id)
            result = await db.execute(stmt)
            subscription = result.scalar_one_or_none()

            if subscription:
                subscription.plan_name = "free"
                subscription.next_billing_date = None

        await db.commit()

        logger.info(f"Webhook processed: payment_key={payment_key}, status={status}")

        return {"success": True, "message": "Webhook processed"}

    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}


# Keep legacy mock endpoint for backward compatibility
@router.get("/plans")
async def get_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {"name": "free", "price": 0, "desc": "Free Tier (3 Hard Matches/day)"},
            {"name": "basic", "price": 10000, "desc": "Basic Tier (50 Hard Matches/day)"},
            {"name": "pro", "price": 30000, "desc": "Pro Tier (Unlimited)"},
        ]
    }
