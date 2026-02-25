"""
User Keywords API 통합 테스트
- POST /api/v1/keywords/ (키워드 추가)
- GET /api/v1/keywords/ (키워드 목록)
- DELETE /api/v1/keywords/{keyword_id} (키워드 삭제)
"""

from httpx import AsyncClient


class TestCreateUserKeyword:
    """유저 키워드 추가"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/keywords/",
            json={"keyword": "구내식당", "category": "include"},
        )
        assert response.status_code == 401

    async def test_create_success(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post(
            "/api/v1/keywords/",
            json={"keyword": "구내식당", "category": "include", "is_active": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["keyword"] == "구내식당"
        assert data["category"] == "include"

    async def test_create_duplicate(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/keywords/",
            json={"keyword": "중복키워드", "category": "include"},
        )
        response = await authenticated_client.post(
            "/api/v1/keywords/",
            json={"keyword": "중복키워드", "category": "include"},
        )
        assert response.status_code == 400


class TestReadUserKeywords:
    """유저 키워드 목록 조회"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/keywords/")
        assert response.status_code == 401

    async def test_empty(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/keywords/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_with_keywords(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/keywords/",
            json={"keyword": "조회테스트", "category": "include"},
        )
        response = await authenticated_client.get("/api/v1/keywords/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestDeleteUserKeyword:
    """유저 키워드 삭제"""

    async def test_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.delete("/api/v1/keywords/1")
        assert response.status_code == 401

    async def test_delete_nonexistent(self, authenticated_client: AsyncClient):
        response = await authenticated_client.delete("/api/v1/keywords/99999")
        assert response.status_code == 404

    async def test_delete_success(self, authenticated_client: AsyncClient):
        create_resp = await authenticated_client.post(
            "/api/v1/keywords/",
            json={"keyword": "삭제대상", "category": "include"},
        )
        keyword_id = create_resp.json()["id"]
        response = await authenticated_client.delete(f"/api/v1/keywords/{keyword_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Deleted"
