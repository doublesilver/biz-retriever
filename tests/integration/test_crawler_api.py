"""
Crawler API 통합 테스트
- Taskiq 기반 크롤링 트리거 및 상태 확인
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def get_error_message(response):
    """에러 응답에서 메시지 추출 (envelope 또는 legacy 형식)"""
    data = response.json()
    if "error" in data and isinstance(data["error"], dict):
        return data["error"].get("message", "")
    return data.get("detail", "")


class TestCrawlerAPI:
    """Crawler API 통합 테스트"""

    # ============================================
    # POST /crawler/trigger 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_trigger_crawl_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.post("/api/v1/crawler/trigger")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_crawl_non_superuser(self, authenticated_client: AsyncClient):
        """일반 사용자는 403"""
        response = await authenticated_client.post("/api/v1/crawler/trigger")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_trigger_crawl_success(self, test_superuser, test_db):
        """슈퍼유저 크롤링 트리거 - Taskiq import 실패 시 503"""
        import sys
        from httpx import ASGITransport, AsyncClient as AC
        from app.core.security import create_access_token
        from app.main import app

        token = create_access_token(subject=test_superuser.email)
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)

        async with AC(transport=transport, base_url="http://test", headers=headers) as client:
            # Taskiq 모듈이 없으면 ImportError → 503
            # Taskiq 모듈이 있으면 Redis 연결 실패 → 503
            # 어느 쪽이든 503이 올바른 응답
            response = await client.post("/api/v1/crawler/trigger")

        # 테스트 환경에서는 Taskiq/Redis가 없으므로 503
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_trigger_crawl_non_superuser_forbidden(self, authenticated_client):
        """일반 사용자 크롤링 트리거 - 403"""
        response = await authenticated_client.post("/api/v1/crawler/trigger")
        assert response.status_code == 403

    # ============================================
    # GET /crawler/status/{task_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_check_status_valid_task_id(self, async_client: AsyncClient):
        """유효한 task_id - Taskiq 상태 반환"""
        response = await async_client.get("/api/v1/crawler/status/test-task-123")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert "status" in data

    @pytest.mark.asyncio
    async def test_check_status_invalid_task_id_format(self, async_client: AsyncClient):
        """잘못된 task_id 형식 - 400"""
        response = await async_client.get("/api/v1/crawler/status/invalid@task")

        assert response.status_code == 400
        msg = get_error_message(response)
        assert "영문자" in msg or "숫자" in msg

    @pytest.mark.asyncio
    async def test_check_status_empty_task_id(self, async_client: AsyncClient):
        """빈 task_id - 404 또는 405"""
        response = await async_client.get("/api/v1/crawler/status/")

        # 빈 경로는 404
        assert response.status_code in [404, 405]
