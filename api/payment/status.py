"""
GET /api/payment/status?orderId=xxx
결제 상태 조회 API
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
from pydantic import BaseModel
from urllib.parse import urlparse, parse_qs

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight
from lib.auth import require_auth
from lib.db import get_db
from app.services.payment_service import payment_service
from app.db.models import User, PaymentHistory
from sqlalchemy import select


# Response Schema
class PaymentStatusResponse(BaseModel):
    orderId: str
    status: str  # pending, paid, failed, refunded
    amount: float
    currency: str
    payment_method: str
    created_at: str
    updated_at: str


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """결제 상태 조회"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. Query parameter 파싱
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            order_id = query_params.get("orderId", [None])[0]
            
            if not order_id:
                send_error(self, 400, "Missing orderId query parameter")
                return
            
            # 3. 비동기 처리
            result = asyncio.run(self.get_payment_status(user_payload, order_id))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_payment_status(self, user_payload: dict, order_id: str):
        """결제 상태 조회 로직"""
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
            
            # 2. Find payment in PaymentHistory
            payment_query = select(PaymentHistory).where(
                PaymentHistory.transaction_id == order_id,
                PaymentHistory.user_id == user_id
            )
            payment_result = await db.execute(payment_query)
            payment = payment_result.scalar_one_or_none()
            
            if not payment:
                raise ValueError("Payment not found")
            
            # 3. Return payment status
            # Note: We could optionally call payment_service.get_payment_info()
            # to get real-time status from Tosspayments, but that requires paymentKey
            # which we don't store. For now, use our database status.
            return PaymentStatusResponse(
                orderId=payment.transaction_id or order_id,
                status=payment.status,
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                created_at=payment.created_at.isoformat(),
                updated_at=payment.updated_at.isoformat()
            )
