"""
Crawler API 통합 테스트
"""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


class TestCrawlerAPI:
    """Crawler API 통합 테스트"""

    # ============================================
    # POST /crawler/crawl/trigger 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_trigger_crawl_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.post("/api/v1/crawler/trigger")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_crawl_success(self, authenticated_client: AsyncClient):
        """크롤링 트리거 성공"""
        with patch('app.worker.tasks.crawl_g2b_bids') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task-id-123"
            mock_task.delay.return_value = mock_result

            response = await authenticated_client.post("/api/v1/crawler/trigger")

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_trigger_crawl_exception(self, authenticated_client: AsyncClient):
        """크롤링 트리거 실패 (예외 발생) - 503 Service Unavailable"""
        with patch('app.worker.tasks.crawl_g2b_bids') as mock_task:
            # Mock exception
            mock_task.delay.side_effect = Exception("Redis connection failed")

            response = await authenticated_client.post("/api/v1/crawler/trigger")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "크롤링 서비스를 시작할 수 없습니다" in data["detail"]


    # ============================================
    # GET /crawler/status/{task_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_check_status_success(self, async_client: AsyncClient):
        """작업 상태 확인"""
        with patch('app.api.endpoints.crawler.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.state = "PENDING"
            mock_task.ready.return_value = False
            mock_task.result = None
            mock_async_result.return_value = mock_task

            response = await async_client.get("/api/v1/crawler/status/test-task-123")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-123"
            assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_check_status_completed(self, async_client: AsyncClient):
        """완료된 작업 상태 확인"""
        with patch('app.api.endpoints.crawler.AsyncResult') as mock_async_result:
            mock_task = MagicMock()
            mock_task.state = "SUCCESS"
            mock_task.ready.return_value = True
            mock_task.result = {"count": 5}
            mock_async_result.return_value = mock_task

            response = await async_client.get("/api/v1/crawler/status/test-task-456")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SUCCESS"
            assert data["result"] == {"count": 5}

    @pytest.mark.asyncio
    async def test_check_status_invalid_task_id_format(self, async_client: AsyncClient):
        """잘못된 task_id 형식 - 400"""
        response = await async_client.get("/api/v1/crawler/status/invalid@task#id")

        assert response.status_code == 400
        data = response.json()
        assert "영문자" in data["detail"] or "숫자" in data["detail"]

    @pytest.mark.asyncio
    async def test_check_status_empty_task_id(self, async_client: AsyncClient):
        """빈 task_id - 404 또는 422"""
        response = await async_client.get("/api/v1/crawler/status/")

        # 빈 경로는 404
        assert response.status_code in [404, 405]
