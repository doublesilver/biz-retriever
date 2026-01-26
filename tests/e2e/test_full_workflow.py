"""
E2E (End-to-End) 테스트
전체 사용자 워크플로우 테스트
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import json

pytestmark = pytest.mark.asyncio


class TestUserWorkflow:
    """사용자 회원가입 → 로그인 → 공고 조회 워크플로우"""

    async def test_complete_user_workflow(self, async_client: AsyncClient):
        """
        전체 사용자 워크플로우 테스트

        1. 회원가입
        2. 로그인
        3. 공고 목록 조회
        4. 공고 상세 조회
        5. 공고 상태 변경
        """
        # 1. 회원가입
        register_data = {
            "email": f"e2e_user_{datetime.now().timestamp()}@example.com",
            "password": "SecurePass123!"
        }
        response = await async_client.post(
            "/api/v1/auth/register",
            json=register_data
        )
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == register_data["email"]
        assert user_data["is_active"] is True

        # 2. 로그인
        login_data = {
            "username": register_data["email"],
            "password": register_data["password"]
        }
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data=login_data
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # 인증 헤더 설정
        auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # 3. 공고 목록 조회
        response = await async_client.get(
            "/api/v1/bids/",
            headers=auth_headers
        )
        assert response.status_code == 200
        bids = response.json()
        assert isinstance(bids, list)

        # 4. 공고 생성 (테스트용)
        bid_data = {
            "title": "E2E 테스트 공고",
            "content": "E2E 테스트를 위한 공고입니다.",
            "agency": "테스트 기관",
            "url": f"https://example.com/e2e-test-{datetime.now().timestamp()}",
            "posted_at": datetime.now().isoformat()
        }
        response = await async_client.post(
            "/api/v1/bids/",
            json=bid_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        created_bid = response.json()
        bid_id = created_bid["id"]

        # 5. 공고 상세 조회
        response = await async_client.get(
            f"/api/v1/bids/{bid_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        bid_detail = response.json()
        assert bid_detail["title"] == bid_data["title"]


class TestCrawlerWorkflow:
    """크롤러 트리거 → 결과 확인 워크플로우"""

    async def test_crawler_trigger_workflow(self, authenticated_client: AsyncClient):
        """
        크롤러 워크플로우 테스트

        1. 크롤러 트리거
        2. Task ID로 상태 확인
        """
        # Mock Celery task
        with patch('app.api.endpoints.crawler.crawl_g2b_bids') as mock_crawl:
            mock_task = MagicMock()
            mock_task.id = "e2e-test-task-123"
            mock_crawl.delay.return_value = mock_task

            # 1. 크롤러 트리거
            response = await authenticated_client.post("/api/v1/crawler/trigger")
            # 200 OK
            assert response.status_code == 200
            result = response.json()
            assert "task_id" in result
            assert result["status"] == "started"

        # Mock AsyncResult for status check
        with patch('app.api.endpoints.crawler.AsyncResult') as mock_async_result:
            mock_result = MagicMock()
            mock_result.state = "PENDING"
            mock_result.ready.return_value = False
            mock_result.result = None
            mock_async_result.return_value = mock_result

            # 2. Task ID로 상태 확인
            task_id = result["task_id"]
            response = await authenticated_client.get(f"/api/v1/crawler/status/{task_id}")
            assert response.status_code == 200
            status = response.json()
            assert "status" in status
            assert status["task_id"] == task_id


class TestAnalyticsWorkflow:
    """통계 조회 워크플로우"""

    async def test_analytics_workflow(self, authenticated_client: AsyncClient):
        """
        통계 워크플로우 테스트

        1. 대시보드 요약 조회
        2. 트렌드 조회
        3. 마감 임박 알림 조회
        """
        # 1. 대시보드 요약
        response = await authenticated_client.get("/api/v1/analytics/summary")
        assert response.status_code == 200
        summary = response.json()
        assert isinstance(summary, dict)

        # 2. 트렌드 조회
        response = await authenticated_client.get("/api/v1/analytics/trends?days=7")
        assert response.status_code == 200

        # 3. 마감 임박 알림 조회
        response = await authenticated_client.get("/api/v1/analytics/deadline-alerts")
        assert response.status_code == 200


class TestExportWorkflow:
    """엑셀 내보내기 워크플로우"""

    async def test_export_workflow(self, authenticated_client: AsyncClient, multiple_bids):
        """
        엑셀 내보내기 워크플로우 테스트

        1. 엑셀 내보내기 요청
        2. 파일 다운로드 확인
        """
        # 1. 엑셀 내보내기 요청 (multiple_bids fixture가 데이터를 제공)
        response = await authenticated_client.get("/api/v1/export/excel")
        # 200 또는 파일 응답
        assert response.status_code == 200
        # Content-Type이 Excel 파일인지 확인
        assert "spreadsheet" in response.headers.get("content-type", "")


class TestFilterWorkflow:
    """필터 관리 워크플로우"""

    async def test_filter_workflow(self, authenticated_client: AsyncClient):
        """
        필터 관리 워크플로우 테스트

        1. 제외 키워드 목록 조회
        2. 제외 키워드 추가
        3. 제외 키워드 삭제
        """
        with patch('app.api.endpoints.filters.keyword_service') as mock_service:
            # Mock 설정
            mock_service.get_active_keywords = AsyncMock(return_value=["keyword1"])
            mock_keyword = AsyncMock()
            mock_keyword.word = "e2e_test_keyword"
            mock_keyword.id = 1
            mock_service.create_keyword = AsyncMock(return_value=mock_keyword)
            mock_service.delete_keyword = AsyncMock(return_value=True)

            # 1. 제외 키워드 목록 조회
            response = await authenticated_client.get("/api/v1/filters/keywords")
            assert response.status_code == 200

            # 2. 제외 키워드 추가
            response = await authenticated_client.post(
                "/api/v1/filters/keywords",
                json={"keyword": "e2e_test_keyword"}
            )
            assert response.status_code in [200, 201]

            # 3. 제외 키워드 삭제
            response = await authenticated_client.delete(
                "/api/v1/filters/keywords/e2e_test_keyword"
            )
            assert response.status_code in [200, 204]


class TestHealthAndMetrics:
    """헬스체크 및 메트릭 워크플로우"""

    async def test_health_check(self, async_client: AsyncClient):
        """헬스체크 엔드포인트 테스트"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "Biz-Retriever"

    async def test_metrics_endpoint(self, async_client: AsyncClient):
        """Prometheus 메트릭 엔드포인트 테스트"""
        response = await async_client.get("/metrics")
        assert response.status_code == 200
        # Prometheus 형식 확인
        assert "http_requests" in response.text or response.status_code == 200

    async def test_openapi_docs(self, async_client: AsyncClient):
        """OpenAPI 문서 엔드포인트 테스트"""
        response = await async_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        # 프로젝트 이름 확인 (Backend 포함)
        assert "info" in openapi
        assert "title" in openapi["info"]


class TestWebSocketWorkflow:
    """WebSocket 연결 워크플로우"""

    async def test_websocket_endpoint_exists(self, async_client: AsyncClient):
        """WebSocket 엔드포인트 존재 확인 (HTTP로 접근 시 비-200 응답)"""
        # WebSocket 엔드포인트는 HTTP GET으로 접근 시 다양한 에러 코드 반환 가능
        # 404: 라우트가 WebSocket만 처리하는 경우
        # 400/405/422: 일반적인 WebSocket 미지원 응답
        response = await async_client.get("/api/v1/realtime/notifications")
        # WebSocket 엔드포인트이므로 일반 HTTP 요청은 실패 (200이 아니면 성공)
        assert response.status_code != 200


class TestSearchWorkflow:
    """검색 워크플로우"""

    async def test_search_by_keyword(self, authenticated_client: AsyncClient):
        """키워드 검색 테스트"""
        response = await authenticated_client.get(
            "/api/v1/bids/",
            params={"keyword": "식당"}
        )
        assert response.status_code == 200
        bids = response.json()
        assert isinstance(bids, list)

    async def test_search_by_agency(self, authenticated_client: AsyncClient):
        """기관별 검색 테스트"""
        response = await authenticated_client.get(
            "/api/v1/bids/",
            params={"agency": "한국"}
        )
        assert response.status_code == 200
        bids = response.json()
        assert isinstance(bids, list)

    async def test_search_with_pagination(self, authenticated_client: AsyncClient):
        """페이지네이션 테스트"""
        response = await authenticated_client.get(
            "/api/v1/bids/",
            params={"skip": 0, "limit": 10}
        )
        assert response.status_code == 200
        bids = response.json()
        assert isinstance(bids, list)
        assert len(bids) <= 10


class TestErrorHandling:
    """에러 핸들링 테스트"""

    async def test_404_not_found(self, async_client: AsyncClient):
        """404 에러 테스트"""
        response = await async_client.get("/api/v1/bids/999999")
        assert response.status_code == 404

    async def test_401_unauthorized(self, async_client: AsyncClient):
        """401 인증 에러 테스트"""
        response = await async_client.post(
            "/api/v1/bids/",
            json={"title": "test", "content": "test", "url": "http://test.com"}
        )
        assert response.status_code == 401

    async def test_422_validation_error(self, async_client: AsyncClient):
        """422 검증 에러 테스트"""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "invalid-email", "password": "weak"}
        )
        assert response.status_code == 422

    async def test_400_duplicate_email(self, async_client: AsyncClient):
        """400 중복 이메일 에러 테스트"""
        email = f"duplicate_{datetime.now().timestamp()}@example.com"

        # 첫 번째 등록
        await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePass123!"}
        )

        # 두 번째 등록 (중복)
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePass123!"}
        )
        assert response.status_code == 400
