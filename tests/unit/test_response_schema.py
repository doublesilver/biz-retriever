"""
표준 API 응답 스키마 단위 테스트
- ok() 헬퍼
- ok_paginated() 헬퍼
- fail() 헬퍼
- ApiResponse / ErrorDetail / PaginationMeta 모델
"""

from app.schemas.response import (
    ApiResponse,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    fail,
    ok,
    ok_paginated,
)


class TestOkHelper:
    """ok() 성공 응답 헬퍼 테스트"""

    def test_ok_with_data(self):
        result = ok({"id": 1, "name": "test"})
        assert result["success"] is True
        assert result["data"] == {"id": 1, "name": "test"}
        assert "timestamp" in result
        assert "meta" not in result

    def test_ok_without_data(self):
        result = ok()
        assert result["success"] is True
        assert result["data"] is None

    def test_ok_with_meta(self):
        result = ok({"items": []}, meta={"page": 1, "total": 100})
        assert result["meta"]["page"] == 1
        assert result["meta"]["total"] == 100

    def test_ok_with_list(self):
        result = ok([1, 2, 3])
        assert result["data"] == [1, 2, 3]


class TestOkPaginatedHelper:
    """ok_paginated() 페이지네이션 응답 헬퍼 테스트"""

    def test_basic_pagination(self):
        result = ok_paginated([1, 2, 3], total=100, skip=0, limit=20)
        assert result["success"] is True
        assert result["data"] == [1, 2, 3]
        assert result["meta"]["page"] == 1
        assert result["meta"]["per_page"] == 20
        assert result["meta"]["total"] == 100
        assert result["meta"]["total_pages"] == 5

    def test_second_page(self):
        result = ok_paginated([], total=100, skip=20, limit=20)
        assert result["meta"]["page"] == 2

    def test_last_page(self):
        result = ok_paginated([], total=25, skip=20, limit=10)
        assert result["meta"]["page"] == 3
        assert result["meta"]["total_pages"] == 3

    def test_zero_limit_edge(self):
        """limit=0인 edge case"""
        result = ok_paginated([], total=10, skip=0, limit=0)
        assert result["meta"]["page"] == 1
        assert result["meta"]["total_pages"] == 1

    def test_single_page(self):
        result = ok_paginated([1], total=1, skip=0, limit=100)
        assert result["meta"]["total_pages"] == 1


class TestFailHelper:
    """fail() 에러 응답 헬퍼 테스트"""

    def test_basic_fail(self):
        result = fail(code="AUTH_001", message="Invalid token")
        assert result["success"] is False
        assert result["error"]["code"] == "AUTH_001"
        assert result["error"]["message"] == "Invalid token"
        assert result["error"]["details"] is None
        assert result["error"]["path"] is None
        assert "timestamp" in result

    def test_fail_with_details(self):
        result = fail(
            code="VALIDATION_ERROR",
            message="검증 실패",
            details={"field": "email", "reason": "invalid"},
            path="/api/v1/auth/register",
        )
        assert result["error"]["details"]["field"] == "email"
        assert result["error"]["path"] == "/api/v1/auth/register"


class TestPydanticModels:
    """Pydantic 모델 테스트"""

    def test_error_detail_model(self):
        err = ErrorDetail(code="TEST", message="test msg")
        assert err.code == "TEST"
        assert err.details is None

    def test_pagination_meta(self):
        meta = PaginationMeta(page=1, per_page=20, total=100, total_pages=5)
        assert meta.total_pages == 5

    def test_api_response_success(self):
        resp = ApiResponse(success=True, data={"id": 1})
        assert resp.success is True
        assert resp.error is None

    def test_api_response_failure(self):
        resp = ApiResponse(
            success=False,
            error=ErrorDetail(code="ERR", message="failed"),
        )
        assert resp.success is False
        assert resp.error.code == "ERR"

    def test_error_response_legacy(self):
        """레거시 ErrorResponse 호환성"""
        resp = ErrorResponse(code="TEST", message="msg")
        assert resp.code == "TEST"
        assert resp.details is None
