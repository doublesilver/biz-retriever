"""
POST /api/payment/confirm
결제 승인 API (Tosspayments Confirmation)
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight, parse_json_body
from lib.auth import require_auth
from lib.db import get_db
from app.services.payment_service import payment_service
from app.db.models import User, PaymentHistory, Subscription
from sqlalchemy import select


# Request/Response Schemas
class ConfirmPaymentRequest(BaseModel):
    orderId: str = Field(..., description="Order ID from create payment")
    paymentKey: str = Field(..., description="Payment key from Tosspayments")
    amount: int = Field(..., description="Payment amount for verification")


class SubscriptionInfo(BaseModel):
    plan_name: str
    is_active: bool
    next_billing_date: str


class ConfirmPaymentResponse(BaseModel):
    success: bool
    subscription: SubscriptionInfo


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_POST(self):
        """결제 승인"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 파싱
            req = parse_json_body(self, ConfirmPaymentRequest)
            if not req:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.confirm_payment(user_payload, req))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def confirm_payment(self, user_payload: dict, req: ConfirmPaymentRequest):
        """결제 승인 로직"""
        async for db in get_db():
            # 1. 사용자 조회
            user_id = user_payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid user token")
            
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValueError("User not found")
            
            # 2. Find payment in PaymentHistory by orderId
            payment_query = select(PaymentHistory).where(
                PaymentHistory.transaction_id == req.orderId,
                PaymentHistory.user_id == user_id
            )
            payment_result = await db.execute(payment_query)
            payment = payment_result.scalar_one_or_none()
            
            if not payment:
                raise ValueError("Payment not found")
            
            if payment.status == "paid":
                raise ValueError("Payment already confirmed")
            
            # 3. Verify amount matches
            if payment.amount != req.amount:
                raise ValueError(f"Amount mismatch: expected {payment.amount}, got {req.amount}")
            
            # 4. Call Tosspayments API to confirm payment
            try:
                confirmation_result = await payment_service.confirm_payment(
                    payment_key=req.paymentKey,
                    order_id=req.orderId,
                    amount=req.amount
                )
            except Exception as e:
                # Update payment status to failed
                payment.status = "failed"
                await db.commit()
                raise ValueError(f"Payment confirmation failed: {str(e)}")
            
            # 5. Update PaymentHistory status to paid
            payment.status = "paid"
            await db.commit()
            
            # 6. Update or create user subscription
            # Extract plan name from orderId (format: BIZ-{user_id}-{PLAN}-{timestamp})
            order_parts = req.orderId.split("-")
            if len(order_parts) >= 3:
                plan_name = order_parts[2].lower()  # BASIC or PRO -> basic or pro
            else:
                raise ValueError("Invalid orderId format")
            
            # Check if user has existing subscription
            sub_query = select(Subscription).where(Subscription.user_id == user_id)
            sub_result = await db.execute(sub_query)
            subscription = sub_result.scalar_one_or_none()
            
            # Calculate next billing date (30 days from now)
            next_billing = datetime.utcnow() + timedelta(days=30)
            
            if subscription:
                # Update existing subscription
                subscription.plan_name = plan_name
                subscription.is_active = True
                subscription.next_billing_date = next_billing
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=user_id,
                    plan_name=plan_name,
                    is_active=True,
                    start_date=datetime.utcnow(),
                    next_billing_date=next_billing
                )
                db.add(subscription)
            
            await db.commit()
            
            # 7. Return success response
            return ConfirmPaymentResponse(
                success=True,
                subscription=SubscriptionInfo(
                    plan_name=subscription.plan_name,
                    is_active=subscription.is_active,
                    next_billing_date=subscription.next_billing_date.isoformat()
                )
            )
