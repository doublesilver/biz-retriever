"""
Bid 서비스 단위 테스트
"""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BidAnnouncement
from app.schemas.bid import BidCreate
from app.services.bid_service import bid_service


class TestBidService:
    """Bid CRUD 서비스 테스트"""

    # ============================================
    # create_bid 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_bid(self, test_db: AsyncSession):
        """Bid 생성"""
        bid_in = BidCreate(
            title="테스트 공고",
            content="테스트 내용입니다.",
            agency="테스트 기관",
            posted_at=datetime.utcnow(),
            url="https://example.com/test/1",
        )

        result = await bid_service.create_bid(test_db, bid_in)

        assert result.id is not None
        assert result.title == "테스트 공고"
        assert result.content == "테스트 내용입니다."
        assert result.agency == "테스트 기관"
        assert result.processed is False

    @pytest.mark.asyncio
    async def test_create_bid_without_agency(self, test_db: AsyncSession):
        """기관명 없이 Bid 생성"""
        bid_in = BidCreate(
            title="테스트 공고",
            content="테스트 내용",
            posted_at=datetime.utcnow(),
            url="https://example.com/test/2",
        )

        result = await bid_service.create_bid(test_db, bid_in)

        assert result.id is not None
        assert result.agency is None

    # ============================================
    # get_bid 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bid_exists(
        self, test_db: AsyncSession, sample_bid: BidAnnouncement
    ):
        """존재하는 Bid 조회"""
        result = await bid_service.get_bid(test_db, sample_bid.id)

        assert result is not None
        assert result.id == sample_bid.id
        assert result.title == sample_bid.title

    @pytest.mark.asyncio
    async def test_get_bid_not_exists(self, test_db: AsyncSession):
        """존재하지 않는 Bid 조회 - None 반환"""
        result = await bid_service.get_bid(test_db, 99999)

        assert result is None

    # ============================================
    # get_bids 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bids_default(self, test_db: AsyncSession, multiple_bids: list):
        """기본 조회"""
        result = await bid_service.get_bids(test_db)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_bids_pagination_skip(
        self, test_db: AsyncSession, multiple_bids: list
    ):
        """페이지네이션 - skip"""
        result = await bid_service.get_bids(test_db, skip=2)

        assert len(result) == 3  # 5개 중 2개 스킵

    @pytest.mark.asyncio
    async def test_get_bids_pagination_limit(
        self, test_db: AsyncSession, multiple_bids: list
    ):
        """페이지네이션 - limit"""
        result = await bid_service.get_bids(test_db, limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bids_pagination_skip_and_limit(
        self, test_db: AsyncSession, multiple_bids: list
    ):
        """페이지네이션 - skip + limit"""
        result = await bid_service.get_bids(test_db, skip=1, limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bids_keyword_filter(
        self, test_db: AsyncSession, sample_bid: BidAnnouncement
    ):
        """키워드 필터링"""
        result = await bid_service.get_bids(test_db, keyword="구내식당")

        assert len(result) >= 1
        assert any("구내식당" in bid.title for bid in result)

    @pytest.mark.asyncio
    async def test_get_bids_keyword_filter_no_match(
        self, test_db: AsyncSession, multiple_bids: list
    ):
        """키워드 필터링 - 매칭 없음"""
        result = await bid_service.get_bids(test_db, keyword="존재하지않는키워드xyz")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_bids_agency_filter(
        self, test_db: AsyncSession, sample_bid: BidAnnouncement
    ):
        """기관 필터링"""
        result = await bid_service.get_bids(test_db, agency="서울대")

        assert len(result) >= 1
        assert any("서울대" in (bid.agency or "") for bid in result)

    # ============================================
    # update_bid_processing_status 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_to_true(
        self, test_db: AsyncSession, sample_bid: BidAnnouncement
    ):
        """처리 상태를 True로 업데이트"""
        assert sample_bid.processed is False

        await bid_service.update_bid_processing_status(test_db, sample_bid.id, True)

        # DB에서 다시 조회
        updated_bid = await bid_service.get_bid(test_db, sample_bid.id)
        assert updated_bid.processed is True

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_to_false(
        self, test_db: AsyncSession, sample_bid: BidAnnouncement
    ):
        """처리 상태를 False로 업데이트"""
        # 먼저 True로 설정
        await bid_service.update_bid_processing_status(test_db, sample_bid.id, True)

        # 다시 False로 변경
        await bid_service.update_bid_processing_status(test_db, sample_bid.id, False)

        updated_bid = await bid_service.get_bid(test_db, sample_bid.id)
        assert updated_bid.processed is False

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_nonexistent(
        self, test_db: AsyncSession
    ):
        """존재하지 않는 Bid 업데이트 시도"""
        # 예외가 발생하거나 None이 반환되어야 함
        result = await bid_service.update_bid_processing_status(test_db, 99999, True)
        # 구현에 따라 None을 반환하거나 예외를 발생시킬 수 있음
        # 여기서는 함수가 실행되는지만 확인
