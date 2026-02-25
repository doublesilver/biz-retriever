"""
Bid API 통합 테스트
"""

from datetime import datetime

import pytest
from httpx import AsyncClient


class TestBidsAPI:
    """Bid API 통합 테스트"""

    # ============================================
    # GET /bids/{bid_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bid_exists(self, async_client: AsyncClient, sample_bid):
        """존재하는 Bid 조회"""
        response = await async_client.get(f"/api/v1/bids/{sample_bid.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_bid.id
        assert data["title"] == sample_bid.title

    @pytest.mark.asyncio
    async def test_get_bid_not_exists(self, async_client: AsyncClient):
        """존재하지 않는 Bid - 404"""
        response = await async_client.get("/api/v1/bids/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_bid_invalid_id(self, async_client: AsyncClient):
        """잘못된 ID 형식 - 422"""
        response = await async_client.get("/api/v1/bids/0")  # 0은 유효하지 않음 (ge=1)

        assert response.status_code == 422

    # ============================================
    # GET /bids/ 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bids_default(self, async_client: AsyncClient, multiple_bids):
        """기본 조회 - paginated envelope"""
        response = await async_client.get("/api/v1/bids/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_bids_with_pagination(self, async_client: AsyncClient, multiple_bids):
        """페이지네이션"""
        response = await async_client.get("/api/v1/bids/?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    @pytest.mark.asyncio
    async def test_get_bids_with_keyword(self, async_client: AsyncClient, sample_bid):
        """키워드 필터"""
        response = await async_client.get("/api/v1/bids/?keyword=구내식당")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_bids_with_agency(self, async_client: AsyncClient, sample_bid):
        """기관 필터"""
        response = await async_client.get("/api/v1/bids/?agency=서울대")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_bids_invalid_limit(self, async_client: AsyncClient):
        """잘못된 limit - 422"""
        response = await async_client.get("/api/v1/bids/?limit=1000")  # max 500

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_bids_negative_skip(self, async_client: AsyncClient):
        """음수 skip - 422"""
        response = await async_client.get("/api/v1/bids/?skip=-1")

        assert response.status_code == 422

    # ============================================
    # POST /bids/ 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_bid_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        bid_data = {
            "title": "테스트 공고",
            "content": "테스트 내용",
            "posted_at": datetime.utcnow().isoformat(),
            "url": "https://example.com/test",
        }

        response = await async_client.post("/api/v1/bids/", json=bid_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_bid_invalid_data(self, authenticated_client: AsyncClient):
        """유효하지 않은 데이터 - 422"""
        bid_data = {"title": "", "content": "내용"}  # 빈 제목

        response = await authenticated_client.post("/api/v1/bids/", json=bid_data)

        assert response.status_code == 422

    # ============================================
    # POST /bids/upload 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_upload_bid_unauthenticated(self, async_client: AsyncClient):
        """미인증 시 401"""
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        data = {"title": "테스트"}

        response = await async_client.post("/api/v1/bids/upload", files=files, params=data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_bid_unsupported_format(self, authenticated_client: AsyncClient):
        """지원하지 않는 형식 - 400"""
        files = {"file": ("test.txt", b"plain text", "text/plain")}
        data = {"title": "테스트"}

        response = await authenticated_client.post("/api/v1/bids/upload", files=files, params=data)

        assert response.status_code == 400

    # ============================================
    # POST /bids/ 성공 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_bid_success(self, authenticated_client: AsyncClient):
        """공고 생성 성공"""
        bid_data = {
            "title": "새 입찰 공고",
            "content": "공고 상세 내용입니다",
            "agency": "테스트 기관",
            "posted_at": datetime.utcnow().isoformat(),
            "url": "https://example.com/new-bid",
        }
        response = await authenticated_client.post("/api/v1/bids/", json=bid_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "새 입찰 공고"

    # ============================================
    # PATCH /bids/{bid_id} 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_update_bid_unauthenticated(self, async_client: AsyncClient, sample_bid):
        """미인증 시 401"""
        response = await async_client.patch(
            f"/api/v1/bids/{sample_bid.id}",
            json={"status": "reviewing"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_bid_success(self, authenticated_client: AsyncClient, sample_bid):
        """상태 변경 성공"""
        response = await authenticated_client.patch(
            f"/api/v1/bids/{sample_bid.id}",
            json={"status": "reviewing"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_bid_not_found(self, authenticated_client: AsyncClient):
        """존재하지 않는 공고 수정 - 404"""
        response = await authenticated_client.patch(
            "/api/v1/bids/99999",
            json={"status": "reviewing"},
        )
        assert response.status_code == 404
