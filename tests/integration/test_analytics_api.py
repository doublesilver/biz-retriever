"""
Analytics API 통합 테스트
"""

import pytest
from httpx import AsyncClient


class TestAnalyticsAPI:
    """Analytics API 통합 테스트"""

    # ============================================
    # GET /analytics/summary 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_summary_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/analytics/summary")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_summary_success(self, authenticated_client: AsyncClient, multiple_bids):
        """통계 요약 조회 성공"""
        response = await authenticated_client.get("/api/v1/analytics/summary")

        assert response.status_code == 200
        data = response.json()

        # 필수 필드 확인
        assert "total_bids" in data
        assert "this_week" in data
        assert "high_importance" in data
        assert "average_price" in data
        assert "top_agencies" in data
        assert "by_source" in data
        assert "trend" in data

    @pytest.mark.asyncio
    async def test_summary_empty_db(self, authenticated_client: AsyncClient):
        """빈 DB에서 조회"""
        response = await authenticated_client.get("/api/v1/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_bids"] == 0

    # ============================================
    # GET /analytics/trends 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_trends_default_30_days(self, authenticated_client: AsyncClient, multiple_bids):
        """기본 30일 트렌드"""
        response = await authenticated_client.get("/api/v1/analytics/trends")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_trends_custom_days(self, authenticated_client: AsyncClient, multiple_bids):
        """사용자 지정 기간"""
        response = await authenticated_client.get("/api/v1/analytics/trends?days=7")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_trends_invalid_days_negative(self, authenticated_client: AsyncClient):
        """음수 days - 422"""
        response = await authenticated_client.get("/api/v1/analytics/trends?days=-1")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trends_invalid_days_too_large(self, authenticated_client: AsyncClient):
        """너무 큰 days - 422"""
        response = await authenticated_client.get("/api/v1/analytics/trends?days=1000")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_trends_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/analytics/trends")

        assert response.status_code == 401

    # ============================================
    # GET /analytics/deadline-alerts 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_deadline_alerts_success(self, authenticated_client: AsyncClient, multiple_bids):
        """마감 임박 공고 조회"""
        response = await authenticated_client.get("/api/v1/analytics/deadline-alerts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_deadline_alerts_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/analytics/deadline-alerts")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deadline_alerts_response_format(self, authenticated_client: AsyncClient, multiple_bids):
        """응답 형식 확인"""
        response = await authenticated_client.get("/api/v1/analytics/deadline-alerts")

        assert response.status_code == 200
        data = response.json()

        # 데이터가 있으면 형식 확인
        if len(data) > 0:
            alert = data[0]
            assert "id" in alert
            assert "title" in alert
            assert "deadline" in alert
            assert "hours_left" in alert
