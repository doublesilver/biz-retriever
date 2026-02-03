"""
POST /api/payment/create
결제 생성 API (Tosspayments Integration)
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field
from typing import Literal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight, parse_json_body
from lib.auth import require_auth
from lib.db import get_db
from app.services.payment_service import payment_service
from app.services.subscription_service import subscription_service
from app.db.models import User, PaymentHistory
from sqlalchemy import select, text


# Request/Response Schemas
class CreatePaymentRequest(BaseModel):
    plan: Literal["basic", "pro"] = Field(..., description="Subscription plan")
    payment_method: Literal["card", "transfer"] = Field(default="card", description="Payment method")


class CreatePaymentResponse(BaseModel):
    orderId: str
    amount: int
    client_key: str
    successUrl: str
    failUrl: str


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_POST(self):
        """결제 생성"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 파싱
            req = parse_json_body(self, CreatePaymentRequest)
            if not req:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.create_payment(user_payload, req))
            
            # 4. 응답
            send_json(self, 201, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def create_payment(self, user_payload: dict, req: CreatePaymentRequest):
        """결제 생성 로직"""
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
            
            # 2. Generate unique orderId (idempotency key)
            order_id = payment_service.generate_order_id(user_id, req.plan)
            
            # 3. Idempotency check - orderId already exists?
            existing_query = select(PaymentHistory).where(
                PaymentHistory.transaction_id == order_id
            )
            existing = await db.execute(existing_query)
            existing_payment = existing.scalar_one_or_none()
            
            if existing_payment:
                # 409 Conflict - duplicate payment attempt
                raise ValueError("Payment already exists with this orderId")
            
            # 4. Get plan price
            plan_limits = await subscription_service.get_plan_limits(req.plan)
            # Use payment_service for actual pricing (more accurate)
            amount = payment_service.get_plan_amount(req.plan)
            
            if amount == 0:
                raise ValueError("Invalid plan or free plan selected")
            
            # 5. Create payment request (Tosspayments client-side data)
            payment_data = await payment_service.create_payment(
                amount=amount,
                order_id=order_id,
                order_name=f"{req.plan.capitalize()} Plan Subscription",
                customer_email=user.email,
                customer_name=user.email.split("@")[0]  # Simple name from email
            )
            
            # 6. Save to PaymentHistory (pending status)
            payment_history = PaymentHistory(
                user_id=user_id,
                amount=amount,
                currency="KRW",
                status="pending",
                payment_method=req.payment_method,
                transaction_id=order_id
            )
            db.add(payment_history)
            await db.commit()
            
            # 7. Return payment data for frontend
            return CreatePaymentResponse(
                orderId=payment_data["orderId"],
                amount=payment_data["amount"],
                client_key=payment_data["client_key"],
                successUrl=payment_data["successUrl"],
                failUrl=payment_data["failUrl"]
            )
