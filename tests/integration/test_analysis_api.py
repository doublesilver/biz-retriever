"""
Analysis API 통합 테스트
"""
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
        """투찰가 예측 성공"""
        response = await authenticated_client.get(
            f"/api/v1/analysis/predict-price/{sample_bid.id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert "announcement_id" in data
        assert "announcement_title" in data
        assert "estimated_price" in data
        assert "prediction" in data

        prediction = data["prediction"]
        assert "recommended_price" in prediction
        assert "confidence" in prediction

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
        from app.db.models import BidAnnouncement
        from datetime import datetime

        # 추정가 없는 공고 생성
        bid = BidAnnouncement(
            title="추정가 없는 테스트 공고",
            content="테스트 내용",
            agency="테스트 기관",
            posted_at=datetime.utcnow(),
            url="https://example.com/no-price",
            estimated_price=None  # 추정가 없음
        )
        test_db.add(bid)
        await test_db.commit()
        await test_db.refresh(bid)

        response = await authenticated_client.get(f"/api/v1/analysis/predict-price/{bid.id}")

        assert response.status_code == 400
        assert "추정가" in response.json()["detail"]
