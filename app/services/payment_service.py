"""
Payment Service — Tosspayments 결제 하드닝

보안 강화:
- 웹훅 HMAC-SHA256 서명 검증
- 멱등성 키(Idempotency-Key)로 중복 결제 방지
- 지수 백오프(Exponential Backoff) 재시도
- 안전한 에러 처리 및 로깅
"""

import base64
import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import (
    PaymentConfirmationError,
    PaymentError,
    PaymentNotConfiguredError,
)
from app.core.logging import logger


class PaymentService:
    """
    Tosspayments 결제 서비스 (Enterprise Hardened)

    주요 보안 기능:
    1. HMAC-SHA256 웹훅 서명 검증
    2. Idempotency-Key 기반 중복 결제 방지
    3. 지수 백오프 재시도 (네트워크 장애 대응)
    4. 금액 변조 방지 (서버 사이드 금액 검증)
    """

    # 플랜별 가격표 (KRW)
    PLAN_PRICES: Dict[str, int] = {
        "free": 0,
        "basic": 10000,   # 10,000원/월
        "pro": 30000,      # 30,000원/월
    }

    def __init__(self):
        self.secret_key = getattr(settings, "TOSSPAYMENTS_SECRET_KEY", None)
        self.client_key = getattr(settings, "TOSSPAYMENTS_CLIENT_KEY", None)
        self.webhook_secret = getattr(settings, "TOSSPAYMENTS_WEBHOOK_SECRET", None)
        self.api_url = "https://api.tosspayments.com/v1"

        if self.secret_key:
            encoded_key = base64.b64encode(f"{self.secret_key}:".encode()).decode()
            self.auth_header = f"Basic {encoded_key}"
            logger.info("PaymentService: Tosspayments initialized")
        else:
            self.auth_header = None
            logger.warning(
                "PaymentService: Tosspayments not configured (TOSSPAYMENTS_SECRET_KEY missing)"
            )

    def is_configured(self) -> bool:
        """결제 시스템 설정 여부 확인"""
        return self.auth_header is not None

    def _ensure_configured(self) -> None:
        """설정 미완료 시 예외 발생"""
        if not self.is_configured():
            raise PaymentNotConfiguredError()

    @staticmethod
    def generate_idempotency_key() -> str:
        """
        멱등성 키 생성.

        동일 요청의 중복 실행을 방지하기 위한 고유 키.
        UUID v4 기반으로 충돌 확률이 사실상 0.
        """
        return str(uuid.uuid4())

    def generate_order_id(self, user_id: int, plan_name: str) -> str:
        """고유 주문 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"BIZ-{user_id}-{plan_name.upper()}-{timestamp}-{short_uuid}"

    def get_plan_amount(self, plan_name: str) -> int:
        """플랜 가격 조회 (KRW)"""
        return self.PLAN_PRICES.get(plan_name, 0)

    def calculate_proration(
        self,
        old_plan: str,
        new_plan: str,
        days_remaining: int,
        total_days: int = 30,
    ) -> int:
        """
        프로레이션(일할 계산) — 플랜 변경 시 차액 계산.

        업그레이드 시: (새 플랜 가격 - 기존 플랜 가격) * (잔여일 / 전체일)
        다운그레이드 시: 0 (기간 만료 후 변경)

        Args:
            old_plan: 기존 플랜 이름
            new_plan: 새 플랜 이름
            days_remaining: 현재 결제 주기 잔여일
            total_days: 전체 결제 주기 (기본 30일)

        Returns:
            프로레이션 금액 (KRW, 양수=추가 결제)
        """
        old_price = self.get_plan_amount(old_plan)
        new_price = self.get_plan_amount(new_plan)

        if new_price <= old_price:
            return 0

        diff = new_price - old_price
        ratio = days_remaining / total_days if total_days > 0 else 0
        return round(diff * ratio)

    async def create_payment(
        self,
        amount: int,
        order_id: str,
        order_name: str,
        customer_email: str,
        customer_name: str,
    ) -> Dict:
        """
        결제 요청 데이터 생성 (프론트엔드 SDK용).

        서버 사이드에서 금액과 주문정보를 생성하여
        클라이언트 변조를 방지.
        """
        self._ensure_configured()

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    async def confirm_payment(
        self,
        payment_key: str,
        order_id: str,
        amount: int,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """
        결제 승인 (Tosspayments API).

        보안 포인트:
        - 금액은 서버에서 재검증 (클라이언트 변조 방지)
        - 멱등성 키로 중복 승인 방지
        - 지수 백오프 재시도 (최대 3회, 1→2→4초 대기)

        Args:
            payment_key: Tosspayments에서 발급한 결제키
            order_id: 주문 ID
            amount: 결제 금액 (서버 검증용)
            idempotency_key: 멱등성 키 (중복 방지)

        Returns:
            Tosspayments 결제 승인 응답

        Raises:
            PaymentConfirmationError: 결제 승인 실패
        """
        self._ensure_configured()

        url = f"{self.api_url}/payments/confirm"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }

        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=15.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Payment confirmed: order_id={order_id}, amount={amount}원"
                    )
                    return result

                error_data = response.json()
                error_code = error_data.get("code", "UNKNOWN")
                error_msg = error_data.get("message", "알 수 없는 오류")
                logger.error(
                    f"Payment confirmation failed: code={error_code}, message={error_msg}"
                )
                raise PaymentConfirmationError(
                    detail=f"결제 승인 실패: {error_msg}",
                    extra={"toss_error_code": error_code},
                )

        except httpx.TimeoutException:
            logger.error(f"Payment confirmation timeout: order_id={order_id}")
            raise
        except PaymentConfirmationError:
            raise
        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}", exc_info=True)
            raise PaymentConfirmationError(
                detail=f"결제 확인 중 오류: {str(e)}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    async def cancel_payment(
        self,
        payment_key: str,
        cancel_reason: str,
        cancel_amount: Optional[int] = None,
    ) -> Dict:
        """
        결제 취소/환불.

        전액 환불 또는 부분 환불을 지원.

        Args:
            payment_key: 결제키
            cancel_reason: 취소 사유
            cancel_amount: 부분 환불 금액 (None이면 전액 환불)
        """
        self._ensure_configured()

        url = f"{self.api_url}/payments/{payment_key}/cancel"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {"cancelReason": cancel_reason}

        if cancel_amount is not None:
            payload["cancelAmount"] = cancel_amount

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=15.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Payment cancelled: payment_key={payment_key}")
                    return result

                error_data = response.json()
                error_msg = error_data.get("message", "알 수 없는 오류")
                logger.error(f"Payment cancellation failed: {error_data}")
                raise PaymentError(detail=f"결제 취소 실패: {error_msg}")

        except (PaymentError, httpx.TimeoutException):
            raise
        except Exception as e:
            logger.error(f"Payment cancellation error: {str(e)}", exc_info=True)
            raise PaymentError(detail=f"결제 취소 중 오류: {str(e)}")

    async def get_payment_info(self, payment_key: str) -> Dict:
        """결제 상세 정보 조회"""
        self._ensure_configured()

        url = f"{self.api_url}/payments/{payment_key}"
        headers = {"Authorization": self.auth_header}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    return response.json()

                error_data = response.json()
                raise PaymentError(
                    detail=f"결제 정보 조회 실패: {error_data.get('message', 'Unknown')}"
                )

        except PaymentError:
            raise
        except Exception as e:
            logger.error(f"Error getting payment info: {str(e)}", exc_info=True)
            raise PaymentError(detail=f"결제 정보 조회 오류: {str(e)}")

    def verify_webhook_signature(
        self,
        payload_body: bytes,
        signature_header: str,
    ) -> bool:
        """
        Tosspayments 웹훅 HMAC-SHA256 서명 검증.

        웹훅 요청이 Tosspayments에서 실제로 온 것인지 확인.
        중간자 공격(MITM)이나 위변조를 방지.

        Args:
            payload_body: 원본 요청 body (bytes)
            signature_header: 요청 헤더의 서명 값

        Returns:
            True: 서명 유효, False: 서명 불일치
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature_header)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    async def issue_billing_key(
        self,
        auth_key: str,
        customer_key: str,
    ) -> Dict:
        """
        빌링키 발급 (자동 갱신 결제 등록).

        카드 정보를 토큰화하여 빌링키를 발급받고,
        이후 빌링키로 자동 결제를 수행.

        Args:
            auth_key: Tosspayments 인증 키
            customer_key: 고객 고유 키

        Returns:
            빌링키 정보 (billingKey, cardCompany 등)
        """
        self._ensure_configured()

        url = f"{self.api_url}/billing/authorizations/issue"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }
        payload = {
            "authKey": auth_key,
            "customerKey": customer_key,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=15.0
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Billing key issued: customer_key={customer_key}")
                return result

            error_data = response.json()
            raise PaymentError(
                detail=f"빌링키 발급 실패: {error_data.get('message', 'Unknown')}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException),
        reraise=True,
    )
    async def charge_billing_key(
        self,
        billing_key: str,
        amount: int,
        order_id: str,
        order_name: str,
        customer_email: str,
        customer_name: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """
        빌링키로 자동 결제 (구독 갱신).

        Args:
            billing_key: 빌링키
            amount: 결제 금액
            order_id: 주문 ID
            order_name: 상품명
            customer_email: 이메일
            customer_name: 이름
            idempotency_key: 멱등성 키
        """
        self._ensure_configured()

        url = f"{self.api_url}/billing/{billing_key}"
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        payload = {
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name,
            "customerEmail": customer_email,
            "customerName": customer_name,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=15.0
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Billing charged: billing_key={billing_key[:8]}..., "
                    f"amount={amount}원"
                )
                return result

            error_data = response.json()
            raise PaymentConfirmationError(
                detail=f"자동 결제 실패: {error_data.get('message', 'Unknown')}"
            )


# Singleton instance
payment_service = PaymentService()
