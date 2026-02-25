"""
Enterprise Exception Hierarchy

모든 비즈니스 예외를 HTTP 상태 코드와 도메인별 에러 코드에 매핑하는
구조화된 예외 계층.

사용 패턴:
    raise NotFoundError("bid", bid_id)          # → 404 + BIZ_NOT_FOUND
    raise AuthenticationError("Invalid token")   # → 401 + AUTH_INVALID_CREDENTIALS
    raise WeakPasswordError("Too short")         # → 400 + AUTH_WEAK_PASSWORD

글로벌 핸들러(main.py)가 이 예외를 잡아 ApiResponse 포맷으로 변환.
"""

from typing import Any

# ============================================
# Base Exception
# ============================================


class BizRetrieverError(Exception):
    """
    모든 애플리케이션 예외의 기본 클래스.

    Attributes:
        status_code: HTTP 상태 코드 (기본 500)
        error_code: 도메인별 에러 코드 (예: "AUTH_001")
        detail: 사용자에게 보여줄 에러 메시지
        extra: 디버그/개발용 추가 정보
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str = "서버 오류가 발생했습니다.",
        *,
        extra: dict[str, Any] | None = None,
    ):
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail)


# ============================================
# 4xx Client Errors
# ============================================


class BadRequestError(BizRetrieverError):
    """400 Bad Request — 잘못된 요청"""

    status_code = 400
    error_code = "BAD_REQUEST"

    def __init__(self, detail: str = "잘못된 요청입니다.", **kwargs):
        super().__init__(detail, **kwargs)


class AuthenticationError(BizRetrieverError):
    """401 Unauthorized — 인증 실패"""

    status_code = 401
    error_code = "AUTH_INVALID_CREDENTIALS"

    def __init__(self, detail: str = "인증에 실패했습니다.", **kwargs):
        super().__init__(detail, **kwargs)


class ForbiddenError(BizRetrieverError):
    """403 Forbidden — 권한 없음"""

    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, detail: str = "접근 권한이 없습니다.", **kwargs):
        super().__init__(detail, **kwargs)


class NotFoundError(BizRetrieverError):
    """404 Not Found — 리소스 없음"""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(
        self,
        resource: str = "리소스",
        resource_id: Any = None,
        **kwargs,
    ):
        detail = f"{resource}을(를) 찾을 수 없습니다."
        if resource_id is not None:
            detail = f"{resource} (ID: {resource_id})을(를) 찾을 수 없습니다."
        super().__init__(detail, extra={"resource": resource, "resource_id": resource_id}, **kwargs)


class ConflictError(BizRetrieverError):
    """409 Conflict — 리소스 충돌"""

    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, detail: str = "리소스 충돌이 발생했습니다.", **kwargs):
        super().__init__(detail, **kwargs)


class ValidationError(BizRetrieverError):
    """422 Unprocessable Entity — 유효성 검증 실패"""

    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, field: str, reason: str, **kwargs):
        self.field = field
        self.reason = reason
        super().__init__(
            f"입력값 검증 실패: {field} — {reason}",
            extra={"field": field, "reason": reason},
            **kwargs,
        )


class RateLimitError(BizRetrieverError):
    """429 Too Many Requests — 요청 제한 초과"""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, detail: str = "요청 제한을 초과했습니다. 잠시 후 다시 시도하세요.", **kwargs):
        super().__init__(detail, **kwargs)


# ============================================
# 5xx Server Errors
# ============================================


class ServiceUnavailableError(BizRetrieverError):
    """503 Service Unavailable — 서비스 이용 불가"""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"

    def __init__(self, detail: str = "서비스를 일시적으로 사용할 수 없습니다.", **kwargs):
        super().__init__(detail, **kwargs)


# ============================================
# Domain-Specific: Auth
# ============================================


class WeakPasswordError(BadRequestError):
    """비밀번호 정책 위반"""

    error_code = "AUTH_WEAK_PASSWORD"

    def __init__(self, reason: str = "비밀번호가 보안 요구사항을 충족하지 않습니다."):
        self.reason = reason
        super().__init__(detail=reason)


class AccountLockedError(BadRequestError):
    """계정 잠금 상태"""

    error_code = "AUTH_ACCOUNT_LOCKED"

    def __init__(self, remaining_minutes: int = 0):
        self.remaining_minutes = remaining_minutes
        detail = f"로그인 실패가 너무 많아 계정이 잠겼습니다. {remaining_minutes}분 후 다시 시도하세요."
        super().__init__(detail=detail, extra={"remaining_minutes": remaining_minutes})


class InvalidTokenError(AuthenticationError):
    """유효하지 않은 토큰"""

    error_code = "AUTH_INVALID_TOKEN"

    def __init__(self, detail: str = "유효하지 않은 토큰입니다."):
        super().__init__(detail=detail)


class DuplicateEmailError(ConflictError):
    """이메일 중복"""

    error_code = "AUTH_DUPLICATE_EMAIL"

    def __init__(self, email: str = ""):
        detail = "이미 사용 중인 이메일입니다."
        super().__init__(detail=detail)


# ============================================
# Domain-Specific: Bid
# ============================================


class InsufficientDataError(BadRequestError):
    """ML 학습 데이터 부족"""

    error_code = "BID_INSUFFICIENT_DATA"

    def __init__(self, required: int, actual: int):
        self.required = required
        self.actual = actual
        super().__init__(
            detail=f"학습 데이터가 부족합니다. 필요: {required}건, 현재: {actual}건",
            extra={"required": required, "actual": actual},
        )


class ModelNotTrainedError(BadRequestError):
    """ML 모델 미학습"""

    error_code = "BID_MODEL_NOT_TRAINED"

    def __init__(self):
        super().__init__(detail="ML 모델이 학습되지 않았습니다. 먼저 모델을 학습시켜 주세요.")


# ============================================
# Domain-Specific: Crawler
# ============================================


class CrawlerError(ServiceUnavailableError):
    """크롤러 실패"""

    error_code = "CRAWLER_FAILED"

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(
            detail=f"{source} 크롤러 오류: {message}",
            extra={"source": source},
        )


# ============================================
# Domain-Specific: External API
# ============================================


class ExternalAPIError(ServiceUnavailableError):
    """외부 API 호출 실패"""

    error_code = "EXTERNAL_API_ERROR"

    def __init__(self, api_name: str, status_code: int = None, message: str = None):
        self.api_name = api_name
        self.api_status_code = status_code
        detail = f"외부 API 오류: {api_name}"
        if status_code:
            detail += f" (상태: {status_code})"
        if message:
            detail += f" — {message}"
        super().__init__(
            detail=detail,
            extra={"api_name": api_name, "api_status_code": status_code},
        )


class APIKeyError(BadRequestError):
    """API 키 누락/유효하지 않음"""

    error_code = "EXTERNAL_INVALID_API_KEY"

    def __init__(self, key_name: str):
        self.key_name = key_name
        super().__init__(detail=f"유효하지 않거나 누락된 API 키: {key_name}")


# ============================================
# Domain-Specific: File Processing
# ============================================


class FileProcessingError(BadRequestError):
    """파일 처리 실패"""

    error_code = "FILE_PROCESSING_ERROR"

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        super().__init__(
            detail=f"파일 처리 실패 '{filename}': {reason}",
            extra={"filename": filename, "reason": reason},
        )


# ============================================
# Domain-Specific: Payment
# ============================================


class PaymentError(BadRequestError):
    """결제 처리 오류"""

    error_code = "PAYMENT_ERROR"

    def __init__(self, detail: str = "결제 처리 중 오류가 발생했습니다.", **kwargs):
        super().__init__(detail=detail, **kwargs)


class PaymentNotConfiguredError(ServiceUnavailableError):
    """결제 시스템 미설정"""

    error_code = "PAYMENT_NOT_CONFIGURED"

    def __init__(self):
        super().__init__(detail="결제 시스템이 설정되지 않았습니다. 관리자에게 문의하세요.")


class PaymentConfirmationError(PaymentError):
    """결제 승인 실패"""

    error_code = "PAYMENT_CONFIRMATION_FAILED"

    def __init__(self, detail: str = "결제 승인에 실패했습니다.", **kwargs):
        super().__init__(detail=detail, **kwargs)


class PaymentAlreadyRefundedError(PaymentError):
    """이미 환불된 결제"""

    error_code = "PAYMENT_ALREADY_REFUNDED"

    def __init__(self):
        super().__init__(detail="이미 환불된 결제입니다.")


class WebhookVerificationError(AuthenticationError):
    """웹훅 서명 검증 실패"""

    error_code = "PAYMENT_WEBHOOK_INVALID"

    def __init__(self):
        super().__init__(detail="웹훅 서명 검증에 실패했습니다.")


class SubscriptionError(BadRequestError):
    """구독 관련 오류"""

    error_code = "SUBSCRIPTION_ERROR"

    def __init__(self, detail: str = "구독 처리 중 오류가 발생했습니다.", **kwargs):
        super().__init__(detail=detail, **kwargs)


class DuplicateSubscriptionError(ConflictError):
    """이미 동일 플랜 구독 중"""

    error_code = "SUBSCRIPTION_DUPLICATE"

    def __init__(self, plan_name: str):
        super().__init__(detail=f"이미 {plan_name.upper()} 플랜을 사용 중입니다.")


class SubscriptionNotFoundError(NotFoundError):
    """활성 구독 없음"""

    error_code = "SUBSCRIPTION_NOT_FOUND"

    def __init__(self):
        super().__init__(resource="구독")


class InvoiceNotFoundError(NotFoundError):
    """인보이스 없음"""

    error_code = "INVOICE_NOT_FOUND"

    def __init__(self, invoice_id: Any = None):
        super().__init__(resource="인보이스", resource_id=invoice_id)


# ============================================
# Domain-Specific: Database
# ============================================


class DatabaseError(BizRetrieverError):
    """데이터베이스 작업 실패"""

    status_code = 500
    error_code = "DATABASE_ERROR"

    def __init__(self, operation: str, reason: str):
        self.operation = operation
        super().__init__(
            detail=f"데이터베이스 오류 ({operation}): {reason}",
            extra={"operation": operation, "reason": reason},
        )


# ============================================
# Backward Compatibility Aliases
# ============================================

# v1.0.0 코드에서 사용하던 이름들과 호환
BizRetrieverException = BizRetrieverError
