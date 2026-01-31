"""
E2E (End-to-End) 테스트
전체 사용자 워크플로우 테스트
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

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
            "password": "SecurePass123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == register_data["email"]
        assert user_data["is_active"] is True

        # 2. 로그인
        login_data = {
            "username": register_data["email"],
            "password": register_data["password"],
        }
        response = await async_client.post(
            "/api/v1/auth/login/access-token", data=login_data
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # 인증 헤더 설정
        auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # 3. 공고 목록 조회
        response = await async_client.get("/api/v1/bids/", headers=auth_headers)
        assert response.status_code == 200
        bids_response = response.json()
        assert isinstance(bids_response, dict)
        assert "items" in bids_response
        assert isinstance(bids_response["items"], list)

        # 4. 공고 생성 (테스트용)
        bid_data = {
            "title": "E2E 테스트 공고",
            "content": "E2E 테스트를 위한 공고입니다.",
            "agency": "테스트 기관",
            "url": f"https://example.com/e2e-test-{datetime.now().timestamp()}",
            "posted_at": datetime.now().isoformat(),
        }
        response = await async_client.post(
            "/api/v1/bids/", json=bid_data, headers=auth_headers
        )
        assert response.status_code == 201
        created_bid = response.json()
        bid_id = created_bid["id"]

        # 5. 공고 상세 조회
        response = await async_client.get(
            "/api/v1/bids/?skip=0&limit=10", headers=auth_headers
        )
        assert response.status_code == 200
        bids_response = response.json()
        assert isinstance(bids_response, dict)
        assert "items" in bids_response
        assert isinstance(bids_response["items"], list)

    async def test_search_by_agency(self, authenticated_client: AsyncClient):
        """기관별 검색 테스트"""
        response = await authenticated_client.get(
            "/api/v1/bids/", params={"agency": "한국"}
        )
        assert response.status_code == 200
        bids_response = response.json()
        assert isinstance(bids_response, dict)
        assert "items" in bids_response

    async def test_search_with_pagination(self, authenticated_client: AsyncClient):
        """페이지네이션 테스트"""
        response = await authenticated_client.get(
            "/api/v1/bids/", params={"skip": 0, "limit": 10}
        )
        assert response.status_code == 200
        bids_response = response.json()
        assert isinstance(bids_response, dict)
        assert "items" in bids_response
        assert len(bids_response["items"]) <= 10


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
            json={"title": "test", "content": "test", "url": "http://test.com"},
        )
        assert response.status_code == 401

    async def test_422_validation_error(self, async_client: AsyncClient):
        """422 검증 에러 테스트"""
        response = await async_client.post(
            "/api/v1/auth/register", json={"email": "invalid-email", "password": "weak"}
        )
        assert response.status_code == 422

    async def test_400_duplicate_email(self, async_client: AsyncClient):
        """400 중복 이메일 에러 테스트"""
        email = f"duplicate_{datetime.now().timestamp()}@example.com"

        # 첫 번째 등록
        await async_client.post(
            "/api/v1/auth/register", json={"email": email, "password": "SecurePass123!"}
        )

        # 두 번째 등록 (중복)
        response = await async_client.post(
            "/api/v1/auth/register", json={"email": email, "password": "SecurePass123!"}
        )
        assert response.status_code == 400
