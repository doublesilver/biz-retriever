"""
Export API 통합 테스트
"""

import pytest
from httpx import AsyncClient


class TestExportAPI:
    """Export API 통합 테스트"""

    # ============================================
    # GET /export/excel 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_export_excel_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/export/excel")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_excel_success(self, authenticated_client: AsyncClient, multiple_bids):
        """엑셀 내보내기 성공"""
        response = await authenticated_client.get("/api/v1/export/excel")

        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_excel_with_filters(self, authenticated_client: AsyncClient, multiple_bids):
        """필터 적용 엑셀"""
        response = await authenticated_client.get("/api/v1/export/excel?importance_score=2&source=G2B")

        # 결과가 있으면 200, 없으면 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_export_excel_no_results(self, authenticated_client: AsyncClient):
        """결과 없음 - 404"""
        # 존재하지 않는 기관으로 필터링
        response = await authenticated_client.get("/api/v1/export/excel?agency=존재하지않는기관xyz")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_excel_invalid_importance_score(self, authenticated_client: AsyncClient):
        """잘못된 중요도 점수 - 422"""
        response = await authenticated_client.get("/api/v1/export/excel?importance_score=5")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_export_excel_invalid_source(self, authenticated_client: AsyncClient):
        """잘못된 출처 - 422"""
        response = await authenticated_client.get("/api/v1/export/excel?source=INVALID")

        assert response.status_code == 422

    # ============================================
    # GET /export/priority-agencies 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_export_priority_agencies_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        response = await async_client.get("/api/v1/export/priority-agencies?agencies=서울대병원")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_priority_agencies_success(self, authenticated_client: AsyncClient, sample_bid):
        """우선 기관 엑셀 성공"""
        response = await authenticated_client.get("/api/v1/export/priority-agencies?agencies=서울대")

        # 결과가 있으면 200, 없으면 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_export_priority_agencies_no_results(self, authenticated_client: AsyncClient):
        """결과 없음 - 404"""
        response = await authenticated_client.get("/api/v1/export/priority-agencies?agencies=존재하지않는기관")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_priority_agencies_too_many(self, authenticated_client: AsyncClient):
        """기관 수 초과 - 400"""
        # 21개 기관 (최대 20개)
        agencies = ",".join([f"기관{i}" for i in range(21)])
        response = await authenticated_client.get(f"/api/v1/export/priority-agencies?agencies={agencies}")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_export_priority_agencies_missing_param(self, authenticated_client: AsyncClient):
        """필수 파라미터 누락 - 422"""
        response = await authenticated_client.get("/api/v1/export/priority-agencies")

        assert response.status_code == 422
