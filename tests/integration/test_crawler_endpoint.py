"""
크롤러 엔드포인트 통합 테스트
- POST /trigger (관리자 권한, 비관리자 거부)
- GET /status/{task_id} (정상, 유효하지 않은 task_id)
"""

import pytest
from httpx import AsyncClient


class TestTriggerCrawl:
    """POST /api/v1/crawler/trigger 테스트"""

    async def test_non_superuser_forbidden(self, authenticated_client: AsyncClient):
        """비관리자 접근 -> 403"""
        response = await authenticated_client.post("/api/v1/crawler/trigger")
        assert response.status_code == 403

    async def test_superuser_trigger(self, test_db, test_superuser):
        """관리자 크롤링 트리거"""
        from httpx import ASGITransport, AsyncClient
        from app.core.security import create_access_token
        from app.main import app

        token = create_access_token(subject=test_superuser.email)
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
            response = await client.post("/api/v1/crawler/trigger")

        # 503 (taskiq not running) or 200 (success) - both are valid
        assert response.status_code in [200, 503]


class TestCrawlStatus:
    """GET /api/v1/crawler/status/{task_id} 테스트"""

    async def test_valid_task_id(self, async_client: AsyncClient):
        """유효한 task_id"""
        response = await async_client.get("/api/v1/crawler/status/abc-123-def")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "abc-123-def"

    async def test_invalid_task_id(self, async_client: AsyncClient):
        """유효하지 않은 task_id (특수문자)"""
        response = await async_client.get("/api/v1/crawler/status/abc!@#$")
        assert response.status_code == 400
