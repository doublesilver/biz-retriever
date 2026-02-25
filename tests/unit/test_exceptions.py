"""
Enterprise Exception 계층 단위 테스트
- BizRetrieverError 기본 클래스
- 각 도메인별 예외 (Auth, Bid, Crawler, Payment, File, DB)
- HTTP 상태코드/에러코드 매핑
"""

import pytest

from app.core.exceptions import (
    AccountLockedError,
    APIKeyError,
    AuthenticationError,
    BadRequestError,
    BizRetrieverError,
    BizRetrieverException,
    ConflictError,
    CrawlerError,
    DatabaseError,
    DuplicateEmailError,
    ExternalAPIError,
    FileProcessingError,
    ForbiddenError,
    InsufficientDataError,
    InvalidTokenError,
    ModelNotTrainedError,
    NotFoundError,
    PaymentError,
    PaymentNotConfiguredError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    WeakPasswordError,
)


class TestBizRetrieverError:
    """Base exception 테스트"""

    def test_default_values(self):
        err = BizRetrieverError()
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_ERROR"
        assert err.detail == "서버 오류가 발생했습니다."
        assert err.extra == {}

    def test_custom_detail(self):
        err = BizRetrieverError("커스텀 메시지")
        assert err.detail == "커스텀 메시지"
        assert str(err) == "커스텀 메시지"

    def test_extra_info(self):
        err = BizRetrieverError("test", extra={"key": "value"})
        assert err.extra == {"key": "value"}

    def test_backward_compatibility_alias(self):
        assert BizRetrieverException is BizRetrieverError


class TestClientErrors:
    """4xx 클라이언트 에러 테스트"""

    def test_bad_request(self):
        err = BadRequestError("잘못된 요청")
        assert err.status_code == 400
        assert err.error_code == "BAD_REQUEST"

    def test_bad_request_default(self):
        err = BadRequestError()
        assert "잘못된 요청" in err.detail

    def test_authentication_error(self):
        err = AuthenticationError()
        assert err.status_code == 401
        assert err.error_code == "AUTH_INVALID_CREDENTIALS"

    def test_forbidden_error(self):
        err = ForbiddenError()
        assert err.status_code == 403
        assert err.error_code == "FORBIDDEN"

    def test_not_found_error_simple(self):
        err = NotFoundError("공고")
        assert err.status_code == 404
        assert "공고" in err.detail
        assert err.extra["resource"] == "공고"

    def test_not_found_error_with_id(self):
        err = NotFoundError("공고", 123)
        assert "123" in err.detail
        assert err.extra["resource_id"] == 123

    def test_conflict_error(self):
        err = ConflictError()
        assert err.status_code == 409
        assert err.error_code == "CONFLICT"

    def test_validation_error(self):
        err = ValidationError("email", "유효하지 않은 이메일")
        assert err.status_code == 422
        assert err.field == "email"
        assert err.reason == "유효하지 않은 이메일"

    def test_rate_limit_error(self):
        err = RateLimitError()
        assert err.status_code == 429
        assert err.error_code == "RATE_LIMIT_EXCEEDED"


class TestServerErrors:
    """5xx 서버 에러 테스트"""

    def test_service_unavailable(self):
        err = ServiceUnavailableError()
        assert err.status_code == 503


class TestAuthDomainErrors:
    """인증 도메인 에러 테스트"""

    def test_weak_password(self):
        err = WeakPasswordError("비밀번호가 너무 짧습니다")
        assert err.status_code == 400
        assert err.error_code == "AUTH_WEAK_PASSWORD"
        assert err.reason == "비밀번호가 너무 짧습니다"

    def test_account_locked(self):
        err = AccountLockedError(25)
        assert err.remaining_minutes == 25
        assert "25분" in err.detail
        assert err.error_code == "AUTH_ACCOUNT_LOCKED"

    def test_invalid_token(self):
        err = InvalidTokenError()
        assert err.status_code == 401
        assert err.error_code == "AUTH_INVALID_TOKEN"

    def test_duplicate_email(self):
        err = DuplicateEmailError("test@example.com")
        assert err.status_code == 409
        assert err.error_code == "AUTH_DUPLICATE_EMAIL"


class TestBidDomainErrors:
    """입찰 도메인 에러 테스트"""

    def test_insufficient_data(self):
        err = InsufficientDataError(required=100, actual=5)
        assert err.required == 100
        assert err.actual == 5
        assert "100" in err.detail
        assert "5" in err.detail

    def test_model_not_trained(self):
        err = ModelNotTrainedError()
        assert err.error_code == "BID_MODEL_NOT_TRAINED"


class TestCrawlerDomainErrors:
    """크롤러 도메인 에러 테스트"""

    def test_crawler_error(self):
        err = CrawlerError("G2B", "API 타임아웃")
        assert err.status_code == 503
        assert err.source == "G2B"
        assert "G2B" in err.detail


class TestExternalAPIDomainErrors:
    """외부 API 에러 테스트"""

    def test_external_api_error_basic(self):
        err = ExternalAPIError("Gemini")
        assert err.api_name == "Gemini"
        assert "Gemini" in err.detail

    def test_external_api_error_with_status(self):
        err = ExternalAPIError("Gemini", status_code=429, message="Rate limited")
        assert "429" in err.detail
        assert "Rate limited" in err.detail

    def test_api_key_error(self):
        err = APIKeyError("GEMINI_API_KEY")
        assert err.key_name == "GEMINI_API_KEY"


class TestFileProcessingError:

    def test_file_processing(self):
        err = FileProcessingError("test.pdf", "파싱 실패")
        assert err.filename == "test.pdf"
        assert "test.pdf" in err.detail


class TestPaymentDomainErrors:

    def test_payment_error(self):
        err = PaymentError()
        assert err.error_code == "PAYMENT_ERROR"

    def test_payment_not_configured(self):
        err = PaymentNotConfiguredError()
        assert err.status_code == 503


class TestDatabaseError:

    def test_database_error(self):
        err = DatabaseError("INSERT", "connection refused")
        assert err.operation == "INSERT"
        assert "INSERT" in err.detail


class TestExceptionInheritance:
    """상속 계층 테스트"""

    def test_weak_password_inherits_bad_request(self):
        err = WeakPasswordError("test")
        assert isinstance(err, BadRequestError)
        assert isinstance(err, BizRetrieverError)

    def test_crawler_error_inherits_service_unavailable(self):
        err = CrawlerError("G2B", "fail")
        assert isinstance(err, ServiceUnavailableError)

    def test_all_inherit_base(self):
        errors = [
            BadRequestError(),
            AuthenticationError(),
            ForbiddenError(),
            NotFoundError(),
            ConflictError(),
            RateLimitError(),
            ServiceUnavailableError(),
        ]
        for err in errors:
            assert isinstance(err, BizRetrieverError)
