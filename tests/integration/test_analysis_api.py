"""
Analysis API 통합 테스트
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


class TestAnalysisAPI:
    """Analysis API 통합 테스트"""

    # ============================================
    # GET /analysis/predict-price/{announcement_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_predict_price_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/analysis/predict-price/1")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_predict_price_not_found(self, authenticated_client: AsyncClient):
        """공고 없음 - 404"""
        response = await authenticated_client.get("/api/v1/analysis/predict-price/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_predict_price_success(self, authenticated_client: AsyncClient, sample_bid):
        """투찰가 예측 성공 (ML 미학습 시 fallback 포함)"""
        response = await authenticated_client.get(f"/api/v1/analysis/predict-price/{sample_bid.id}")

        assert response.status_code == 200
        data = response.json()

        assert "announcement_id" in data
        assert "announcement_title" in data
        assert "estimated_price" in data
        assert "recommended_price" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_predict_price_invalid_id_zero(self, authenticated_client: AsyncClient):
        """ID가 0인 경우 - 422"""
        response = await authenticated_client.get("/api/v1/analysis/predict-price/0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_price_invalid_id_negative(self, authenticated_client: AsyncClient):
        """음수 ID - 422"""
        response = await authenticated_client.get("/api/v1/analysis/predict-price/-1")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_price_no_estimated_price(self, authenticated_client: AsyncClient, test_db):
        """추정가 없는 공고 - 400"""
        from datetime import datetime

        from app.db.models import BidAnnouncement

        # 추정가 없는 공고 생성
        bid = BidAnnouncement(
            title="추정가 없는 테스트 공고",
            content="테스트 내용",
            agency="테스트 기관",
            posted_at=datetime.utcnow(),
            url="https://example.com/no-price",
            estimated_price=None,  # 추정가 없음
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        response = await authenticated_client.get(f"/api/v1/analysis/predict-price/{bid.id}")

        assert response.status_code == 400
        data = response.json()
        # Envelope format: {"success": false, "error": {"code": "...", "message": "..."}}
        if "error" in data and isinstance(data["error"], dict):
            msg = data["error"].get("message", "")
        else:
            msg = data.get("detail", "")
        assert "추정가" in msg

    # ============================================
    # GET /analysis/match/{announcement_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_match_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/analysis/match/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_match_bid_not_found(self, authenticated_client: AsyncClient):
        """공고 없음 - 404"""
        response = await authenticated_client.get("/api/v1/analysis/match/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_match_no_profile(self, authenticated_client: AsyncClient, sample_bid):
        """프로필 없는 사용자 - 400"""
        response = await authenticated_client.get(f"/api/v1/analysis/match/{sample_bid.id}")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_match_with_profile(self, authenticated_profile_client: AsyncClient, test_db):
        """프로필 있는 사용자의 매칭 확인"""
        from datetime import datetime

        from app.db.models import BidAnnouncement

        bid = BidAnnouncement(
            title="조경공사 입찰",
            content="조경공사 관련 입찰 공고",
            agency="서울시청",
            posted_at=datetime.utcnow(),
            url="https://example.com/match-test",
            estimated_price=100000000,
            region_code="11",
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        response = await authenticated_profile_client.get(f"/api/v1/analysis/match/{bid.id}")
        assert response.status_code == 200
        data = response.json()
        assert "is_match" in data
        assert "reasons" in data
        assert "soft_match" in data

    # ============================================
    # POST /analysis/smart-search 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_smart_search_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.post(
            "/api/v1/analysis/smart-search",
            json={"query": "구내식당"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_smart_search_no_bids(self, authenticated_client: AsyncClient):
        """공고 없는 경우"""
        response = await authenticated_client.post(
            "/api/v1/analysis/smart-search",
            json={"query": "구내식당", "limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_smart_search_with_bids(self, authenticated_client: AsyncClient, multiple_bids):
        """공고가 있지만 Gemini 미설정 시"""
        response = await authenticated_client.post(
            "/api/v1/analysis/smart-search",
            json={"query": "테스트", "limit": 3},
        )
        assert response.status_code == 200
        data = response.json()
        # Gemini 미설정이면 "Gemini Client Not Initialized" 에러 또는 빈 결과
        assert "results" in data

    @pytest.mark.asyncio
    async def test_smart_search_with_gemini_mock(self, authenticated_client: AsyncClient, multiple_bids):
        """Gemini 모킹된 스마트 검색"""
        mock_client = MagicMock()

        async def fake_semantic_match(query, bid):
            return {"score": 0.8, "error": None}

        mock_ms = MagicMock()
        mock_ms.client = mock_client
        mock_ms.calculate_semantic_match = fake_semantic_match

        with patch("app.services.matching_service.matching_service", mock_ms):
            response = await authenticated_client.post(
                "/api/v1/analysis/smart-search",
                json={"query": "구내식당", "limit": 3},
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
