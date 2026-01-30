"""
Payment Service using Tosspayments
Phase 3: Subscription billing system for Korean market
"""

import base64
from datetime import datetime
from typing import Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class PaymentService:
    """
    Tosspayments integration for subscription billing
    https://docs.tosspayments.com/
    """

    def __init__(self):
        # Tosspayments credentials from environment
        self.secret_key = getattr(settings, "TOSSPAYMENTS_SECRET_KEY", None)
        self.client_key = getattr(settings, "TOSSPAYMENTS_CLIENT_KEY", None)
        self.api_url = "https://api.tosspayments.com/v1"

        # Base64 encode secret key for auth header
        if self.secret_key:
            encoded_key = base64.b64encode(f"{self.secret_key}:".encode()).decode()
            self.auth_header = f"Basic {encoded_key}"
            logger.info("PaymentService: Tosspayments initialized")
        else:
            self.auth_header = None
            logger.warning("PaymentService: Tosspayments not configured (TOSSPAYMENTS_SECRET_KEY missing)")

    def is_configured(self) -> bool:
        """Check if Tosspayments is properly configured"""
        return self.auth_header is not None

    async def create_payment(
        self, amount: int, order_id: str, order_name: str, customer_email: str, customer_name: str
    ) -> Dict:
        """
        Create a payment request

        Args:
            amount: Payment amount in KRW (원)
            order_id: Unique order identifier
            order_name: Product/plan name
            customer_email: Customer email
            customer_name: Customer name

        Returns:
            Dict with payment_key, order_id, and redirect URL
        """
        if not self.is_configured():
            raise ValueError("Tosspayments not configured")

        # Note: Tosspayments uses a client-side SDK for payment UI
        # This method prepares the payment data for frontend
        return {
            "client_key": self.client_key,
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name,
            "customerEmail": customer_email,
            "customerName": customer_name,
            "successUrl": f"{settings.FRONTEND_URL}/payment-success",
            "failUrl": f"{settings.FRONTEND_URL}/payment-fail",
        }

    async def confirm_payment(self, payment_key: str, order_id: str, amount: int) -> Dict:
        """
        Confirm a payment (called after user completes payment on Tosspayments UI)

        Args:
            payment_key: Payment key from Tosspayments
            order_id: Order ID
            amount: Payment amount (for verification)

        Returns:
            Payment confirmation result
        """
        if not self.is_configured():
            raise ValueError("Tosspayments not configured")

        url = f"{self.api_url}/payments/confirm"
        headers = {"Authorization": self.auth_header, "Content-Type": "application/json"}
        payload = {"paymentKey": payment_key, "orderId": order_id, "amount": amount}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Payment confirmed: {order_id}, amount: {amount}원")
                    return result
                else:
                    error_data = response.json()
                    logger.error(f"Payment confirmation failed: {error_data}")
                    raise Exception(f"Payment failed: {error_data.get('message', 'Unknown error')}")

        except httpx.TimeoutException:
            logger.error("Payment confirmation timeout")
            raise Exception("결제 확인 요청 시간 초과")
        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}", exc_info=True)
            raise

    async def cancel_payment(self, payment_key: str, cancel_reason: str) -> Dict:
        """
        Cancel/refund a payment

        Args:
            payment_key: Payment key from Tosspayments
            cancel_reason: Reason for cancellation

        Returns:
            Cancellation result
        """
        if not self.is_configured():
            raise ValueError("Tosspayments not configured")

        url = f"{self.api_url}/payments/{payment_key}/cancel"
        headers = {"Authorization": self.auth_header, "Content-Type": "application/json"}
        payload = {"cancelReason": cancel_reason}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Payment cancelled: {payment_key}")
                    return result
                else:
                    error_data = response.json()
                    logger.error(f"Payment cancellation failed: {error_data}")
                    raise Exception(f"Cancellation failed: {error_data.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Payment cancellation error: {str(e)}", exc_info=True)
            raise

    async def get_payment_info(self, payment_key: str) -> Dict:
        """
        Get payment information

        Args:
            payment_key: Payment key from Tosspayments

        Returns:
            Payment details
        """
        if not self.is_configured():
            raise ValueError("Tosspayments not configured")

        url = f"{self.api_url}/payments/{payment_key}"
        headers = {"Authorization": self.auth_header}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    return response.json()
                else:
                    error_data = response.json()
                    logger.error(f"Failed to get payment info: {error_data}")
                    raise Exception(f"Payment info retrieval failed: {error_data.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Error getting payment info: {str(e)}", exc_info=True)
            raise

    def get_plan_amount(self, plan_name: str) -> int:
        """
        Get subscription plan amount in KRW

        Args:
            plan_name: Plan name (free, basic, pro)

        Returns:
            Amount in KRW (원)
        """
        plan_prices = {"free": 0, "basic": 10000, "pro": 30000}  # 10,000원/월  # 30,000원/월
        return plan_prices.get(plan_name, 0)

    def generate_order_id(self, user_id: int, plan_name: str) -> str:
        """
        Generate unique order ID

        Args:
            user_id: User ID
            plan_name: Subscription plan name

        Returns:
            Unique order ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"BIZ-{user_id}-{plan_name.upper()}-{timestamp}"


# Singleton instance
payment_service = PaymentService()
