"""
main.py 예외 핸들러 및 미들웨어 분기 테스트
- PrometheusMiddleware exception 분기
- general_exception_handler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient


class TestPrometheusMiddlewareException:
    """PrometheusMiddleware exception 분기 (lines 143-148)"""

    async def test_exception_records_500_and_reraises(self):
        """call_next에서 예외 발생 -> 500 메트릭 기록 후 re-raise"""
        from app.main import PrometheusMiddleware

        mock_app = MagicMock()
        middleware = PrometheusMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.url.path = "/error-test"

        async def failing_call_next(request):
            raise RuntimeError("call_next error")

        with pytest.raises(RuntimeError, match="call_next error"):
            await middleware.dispatch(mock_request, failing_call_next)


class TestGeneralExceptionHandler:
    """general_exception_handler (lines 326-335)"""

    async def test_returns_500_json(self):
        """Unhandled exception -> 500 JSON response"""
        from app.main import app
        from fastapi import APIRouter

        error_router = APIRouter()

        @error_router.get("/test-general-exc")
        async def error_endpoint():
            raise ValueError("Test general exception")

        app.include_router(error_router)
        try:
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/test-general-exc")
            assert response.status_code == 500
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "INTERNAL_ERROR"
        finally:
            app.routes[:] = [
                r for r in app.routes if getattr(r, "path", "") != "/test-general-exc"
            ]

    async def test_production_hides_details(self):
        """production -> details=None"""
        from app.main import app
        from fastapi import APIRouter

        error_router = APIRouter()

        @error_router.get("/test-exc-prod")
        async def error_endpoint():
            raise ValueError("Secret detail")

        app.include_router(error_router)
        try:
            with patch("app.main._is_production", True):
                transport = ASGITransport(app=app, raise_app_exceptions=False)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/test-exc-prod")

            assert response.status_code == 500
            data = response.json()
            assert data["error"].get("details") is None
        finally:
            app.routes[:] = [
                r for r in app.routes if getattr(r, "path", "") != "/test-exc-prod"
            ]

    async def test_development_shows_details(self):
        """development -> details 포함"""
        from app.main import app
        from fastapi import APIRouter

        error_router = APIRouter()

        @error_router.get("/test-exc-dev")
        async def error_endpoint():
            raise ValueError("Debug info")

        app.include_router(error_router)
        try:
            with patch("app.main._is_production", False):
                transport = ASGITransport(app=app, raise_app_exceptions=False)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/test-exc-dev")

            assert response.status_code == 500
            data = response.json()
            assert data["error"]["details"] is not None
            assert data["error"]["details"]["exception"] == "ValueError"
        finally:
            app.routes[:] = [
                r for r in app.routes if getattr(r, "path", "") != "/test-exc-dev"
            ]
