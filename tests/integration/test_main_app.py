"""
Main App 통합 테스트
- GET / (루트)
- GET /health
- GET /metrics
- Exception handler 테스트
- Security headers 미들웨어
"""

import pytest
from httpx import AsyncClient


class TestRootEndpoint:
    """루트 엔드포인트"""

    async def test_root(self, async_client: AsyncClient):
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["version"] == "1.1.0"


class TestHealthCheck:
    """헬스 체크"""

    async def test_health(self, async_client: AsyncClient):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Biz-Retriever"


class TestMetrics:
    """Prometheus 메트릭"""

    async def test_metrics(self, async_client: AsyncClient):
        response = await async_client.get("/metrics")
        assert response.status_code == 200
        # Prometheus exposition format
        assert "text/plain" in response.headers.get("content-type", "") or \
               "openmetrics" in response.headers.get("content-type", "")


class TestSecurityHeaders:
    """보안 헤더 미들웨어"""

    async def test_security_headers_present(self, async_client: AsyncClient):
        response = await async_client.get("/health")
        headers = response.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert "referrer-policy" in headers
        assert "permissions-policy" in headers
        assert "content-security-policy" in headers
        assert "cache-control" in headers


class TestExceptionHandlers:
    """글로벌 예외 핸들러"""

    async def test_404_envelope(self, async_client: AsyncClient):
        """존재하지 않는 API 경로 요청 시 404"""
        response = await async_client.get("/nonexistent-path")
        assert response.status_code == 404
        data = response.json()
        # FastAPI의 기본 404 핸들러는 HTTPException을 사용하며
        # 우리 커스텀 http_exception_handler가 envelope으로 변환
        assert "detail" in data or "success" in data

    async def test_validation_error_envelope(self, async_client: AsyncClient):
        """유효성 검사 오류 시 envelope 형식"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "short"},
        )
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    async def test_biz_error_handler(self, authenticated_client: AsyncClient):
        """BizRetrieverError 핸들러 (PaymentNotConfiguredError 트리거)"""
        response = await authenticated_client.post(
            "/api/v1/payment/create",
            json={"plan_name": "basic"},
        )
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "code" in data["error"]


class TestHTTPExceptionHandler:
    """HTTP Exception 핸들러 상세 테스트"""

    async def test_http_404_envelope_format(self, async_client: AsyncClient):
        """404 에러가 envelope 형식으로 반환되는지 확인"""
        response = await async_client.get("/api/v1/bids/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]

    async def test_method_not_allowed(self, async_client: AsyncClient):
        """405 Method Not Allowed"""
        response = await async_client.delete("/health")
        assert response.status_code in [405, 404]


class TestBizRetrieverErrorHandler:
    """BizRetrieverError 핸들러 다양한 에러 테스트"""

    async def test_payment_not_configured_503(self, authenticated_client: AsyncClient):
        """PaymentNotConfiguredError -> 503"""
        response = await authenticated_client.post(
            "/api/v1/payment/cancel",
            json={"paymentKey": "pk_test", "cancelReason": "환불"},
        )
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False

    async def test_not_found_error(self, authenticated_client: AsyncClient):
        """NotFoundError -> 404 (공고 없음)"""
        response = await authenticated_client.get(
            "/api/v1/analysis/predict-price/99999"
        )
        assert response.status_code == 404


class TestOpenAPI:
    """OpenAPI/Swagger (개발 환경)"""

    async def test_docs_available(self, async_client: AsyncClient):
        response = await async_client.get("/docs")
        assert response.status_code == 200

    async def test_openapi_json(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
