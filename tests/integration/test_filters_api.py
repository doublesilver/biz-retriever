"""
Filters API 통합 테스트
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient


class TestFiltersAPI:
    """Filters API 통합 테스트"""

    # ============================================
    # POST /filters/exclude-keywords 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_add_exclude_keyword_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.post(
            "/api/v1/filters/exclude-keywords",
            json={"keyword": "테스트"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_exclude_keyword_success(self, authenticated_client: AsyncClient, mock_redis):
        """제외 키워드 추가 성공"""
        with patch('app.api.endpoints.filters.get_redis', return_value=mock_redis):
            response = await authenticated_client.post(
                "/api/v1/filters/exclude-keywords",
                json={"keyword": "테스트키워드"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "테스트키워드" in data["message"]

    @pytest.mark.asyncio
    async def test_add_exclude_keyword_empty(self, authenticated_client: AsyncClient):
        """빈 키워드 - 400 또는 422"""
        response = await authenticated_client.post(
            "/api/v1/filters/exclude-keywords",
            json={"keyword": "   "}  # 공백만
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_add_exclude_keyword_too_long(self, authenticated_client: AsyncClient):
        """너무 긴 키워드 - 422"""
        long_keyword = "a" * 100  # max_length=50
        response = await authenticated_client.post(
            "/api/v1/filters/exclude-keywords",
            json={"keyword": long_keyword}
        )

        assert response.status_code == 422

    # ============================================
    # GET /filters/exclude-keywords 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_exclude_keywords_success(self, async_client: AsyncClient, mock_redis):
        """제외 키워드 목록 조회"""
        with patch('app.api.endpoints.filters.get_redis', return_value=mock_redis):
            response = await async_client.get("/api/v1/filters/exclude-keywords")

            assert response.status_code == 200
            data = response.json()
            assert "keywords" in data
            assert isinstance(data["keywords"], list)

    # ============================================
    # DELETE /filters/exclude-keywords/{keyword} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_delete_exclude_keyword_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.delete("/api/v1/filters/exclude-keywords/테스트")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_exclude_keyword_success(self, authenticated_client: AsyncClient, mock_redis):
        """제외 키워드 삭제 성공"""
        with patch('app.api.endpoints.filters.get_redis', return_value=mock_redis):
            response = await authenticated_client.delete(
                "/api/v1/filters/exclude-keywords/keyword1"
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    @pytest.mark.asyncio
    async def test_delete_exclude_keyword_not_found(self, authenticated_client: AsyncClient):
        """존재하지 않는 키워드 - 404"""
        mock_redis = AsyncMock()
        mock_redis.srem = AsyncMock(return_value=0)  # 삭제된 항목 없음

        with patch('app.api.endpoints.filters.get_redis', return_value=mock_redis):
            response = await authenticated_client.delete(
                "/api/v1/filters/exclude-keywords/존재하지않는키워드"
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_exclude_keyword_too_long(self, authenticated_client: AsyncClient):
        """너무 긴 키워드 - 422"""
        long_keyword = "a" * 100  # max_length=50
        response = await authenticated_client.delete(
            f"/api/v1/filters/exclude-keywords/{long_keyword}"
        )

        assert response.status_code == 422
