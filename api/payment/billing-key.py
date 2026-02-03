"""
POST /api/payment/billing-key
자동결제 (Billing Key) 등록 API
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
from pydantic import BaseModel, Field
import httpx
import base64
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.utils import send_json, send_error, handle_cors_preflight, parse_json_body
from lib.auth import require_auth
from lib.db import get_db
from app.services.payment_service import payment_service
from app.db.models import User, Subscription
from sqlalchemy import select


# Request/Response Schemas
class RegisterBillingKeyRequest(BaseModel):
    customerKey: str = Field(..., description="Unique customer identifier")
    authKey: str = Field(..., description="Auth key from Tosspayments")


class CardInfo(BaseModel):
    card_type: str
    card_company: str
    card_number: str  # Masked


class RegisterBillingKeyResponse(BaseModel):
    billingKey: str
    card_info: CardInfo


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_POST(self):
        """자동결제 등록"""
        try:
            # 1. 인증 체크
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 요청 파싱
            req = parse_json_body(self, RegisterBillingKeyRequest)
            if not req:
                return  # 이미 에러 응답 전송됨
            
            # 3. 비동기 처리
            result = asyncio.run(self.register_billing_key(user_payload, req))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def register_billing_key(self, user_payload: dict, req: RegisterBillingKeyRequest):
        """
        자동결제 등록 로직
        
        NOTE: This implementation calls Tosspayments billing API directly.
        Ideally, this should be refactored to payment_service.register_billing_key()
        """
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
            
            # 2. Tosspayments Billing Key API 호출
            # https://docs.tosspayments.com/reference#%EB%B9%8C%EB%A7%81%ED%82%A4-%EB%B0%9C%EA%B8%89
            if not payment_service.is_configured():
                raise ValueError("Tosspayments not configured")
            
            secret_key = payment_service.secret_key
            api_url = payment_service.api_url
            
            # Base64 encode secret key for auth
            encoded_key = base64.b64encode(f"{secret_key}:".encode()).decode()
            auth_header = f"Basic {encoded_key}"
            
            # Call Tosspayments API
            url = f"{api_url}/billing/authorizations/issue"
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/json",
            }
            payload = {
                "customerKey": req.customerKey,
                "authKey": req.authKey
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url, headers=headers, json=payload, timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        billing_data = response.json()
                        
                        # 3. Store billing key in Subscription
                        # Find or create subscription
                        sub_query = select(Subscription).where(Subscription.user_id == user_id)
                        sub_result = await db.execute(sub_query)
                        subscription = sub_result.scalar_one_or_none()
                        
                        if subscription:
                            # Update with billing key (using stripe_subscription_id field for now)
                            subscription.stripe_subscription_id = billing_data.get("billingKey")
                            await db.commit()
                        else:
                            # Create new subscription with billing key
                            subscription = Subscription(
                                user_id=user_id,
                                plan_name="free",  # Default to free until first payment
                                is_active=True,
                                stripe_subscription_id=billing_data.get("billingKey")
                            )
                            db.add(subscription)
                            await db.commit()
                        
                        # 4. Return billing key info
                        card = billing_data.get("card", {})
                        return RegisterBillingKeyResponse(
                            billingKey=billing_data.get("billingKey", ""),
                            card_info=CardInfo(
                                card_type=card.get("cardType", "신용"),
                                card_company=card.get("issuerCode", "Unknown"),
                                card_number=card.get("number", "****-****-****-****")
                            )
                        )
                    
                    else:
                        error_data = response.json()
                        raise ValueError(
                            f"Billing key registration failed: {error_data.get('message', 'Unknown error')}"
                        )
            
            except httpx.TimeoutException:
                raise ValueError("Billing key registration timeout")
            except httpx.HTTPError as e:
                raise ValueError(f"HTTP error: {str(e)}")
            except Exception as e:
                raise ValueError(f"Billing key registration error: {str(e)}")
