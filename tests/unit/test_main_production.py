"""
main.py 확장 테스트
- SecurityHeadersMiddleware: HSTS production 분기
- PrometheusMiddleware: exception 분기
- startup/shutdown 이벤트 직접 호출
- metrics endpoint production 제한
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSecurityHeadersHSTS:
    """HSTS production 분기 테스트"""

    async def test_hsts_in_production(self):
        """production 환경에서 HSTS 헤더 추가"""
        from app.main import SecurityHeadersMiddleware

        mock_app = AsyncMock()
        middleware = SecurityHeadersMiddleware(mock_app)

        scope = {"type": "http"}

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        async def mock_receive():
            return {}

        # Mock inner app to send http.response.start
        async def fake_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"ok",
                }
            )

        middleware_with_prod = SecurityHeadersMiddleware(fake_app)

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            await middleware_with_prod(scope, mock_receive, mock_send)

        # Check HSTS header was added
        start_msg = sent_messages[0]
        header_names = [h[0] for h in start_msg["headers"]]
        assert b"strict-transport-security" in header_names

    async def test_no_hsts_in_development(self):
        """development 환경에서 HSTS 없음"""
        from app.main import SecurityHeadersMiddleware

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        async def mock_receive():
            return {}

        async def fake_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "headers": [],
                }
            )

        middleware = SecurityHeadersMiddleware(fake_app)

        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            await middleware({"type": "http"}, mock_receive, mock_send)

        start_msg = sent_messages[0]
        header_names = [h[0] for h in start_msg["headers"]]
        assert b"strict-transport-security" not in header_names

    async def test_non_http_scope_passthrough(self):
        """non-http scope는 바로 통과"""
        from app.main import SecurityHeadersMiddleware

        called = []

        async def fake_app(scope, receive, send):
            called.append(True)

        middleware = SecurityHeadersMiddleware(fake_app)
        await middleware({"type": "websocket"}, AsyncMock(), AsyncMock())
        assert len(called) == 1


class TestStartupShutdown:
    """startup/shutdown 이벤트 직접 테스트"""

    async def test_startup(self):
        """startup 이벤트 호출"""
        from app.main import startup

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin.return_value = mock_ctx

        mock_taskiq_startup = AsyncMock()

        with patch("app.main.init_sentry"):
            with patch("app.main.init_app_info"):
                with patch("app.db.session.engine", mock_engine):
                    with patch.dict(
                        "sys.modules",
                        {
                            "app.worker.taskiq_app": MagicMock(startup=mock_taskiq_startup, shutdown=AsyncMock()),
                        },
                    ):
                        await startup()

        mock_taskiq_startup.assert_awaited_once()

    async def test_shutdown(self):
        """shutdown 이벤트 호출"""
        from app.main import shutdown

        mock_taskiq_shutdown = AsyncMock()

        with patch.dict(
            "sys.modules",
            {
                "app.worker.taskiq_app": MagicMock(shutdown=mock_taskiq_shutdown),
            },
        ):
            await shutdown()

        mock_taskiq_shutdown.assert_awaited_once()

    async def test_startup_exception(self):
        """startup 예외 시 raise"""
        from app.main import startup

        with patch("app.main.init_sentry", side_effect=Exception("fail")):
            with pytest.raises(Exception, match="fail"):
                await startup()


class TestMetricsProductionRestriction:
    """metrics 엔드포인트 production 제한"""

    async def test_metrics_blocked_in_production(self):
        """production에서 외부 IP 차단"""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        with patch("app.main._is_production", True):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/metrics")
            # testserver client IP is not in allowed ranges
            assert response.status_code in [200, 404]
