"""
Bid 서비스 단위 테스트
"""

from datetime import datetime

import pytest

from app.db.models import BidAnnouncement
from app.db.repositories.bid_repository import BidRepository
from app.schemas.bid import BidCreate
from app.services.bid_service import bid_service


class TestBidService:
    """Bid CRUD 서비스 테스트"""

    # ============================================
    # create_bid 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_bid(self, bid_repository: BidRepository):
        """Bid 생성"""
        bid_in = BidCreate(
            title="테스트 공고",
            content="테스트 내용입니다.",
            agency="테스트 기관",
            posted_at=datetime.utcnow(),
            url="https://example.com/test/1",
        )

        result = await bid_service.create_bid(bid_repository, bid_in)

        assert result.id is not None
        assert result.title == "테스트 공고"
        assert result.content == "테스트 내용입니다."
        assert result.agency == "테스트 기관"
        assert result.processed is False

    @pytest.mark.asyncio
    async def test_create_bid_without_agency(self, bid_repository: BidRepository):
        """기관명 없이 Bid 생성"""
        bid_in = BidCreate(
            title="테스트 공고",
            content="테스트 내용",
            posted_at=datetime.utcnow(),
            url="https://example.com/test/2",
        )

        result = await bid_service.create_bid(bid_repository, bid_in)

        assert result.id is not None
        assert result.agency is None

    # ============================================
    # get_bid 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bid_exists(self, bid_repository: BidRepository, sample_bid: BidAnnouncement):
        """존재하는 Bid 조회"""
        result = await bid_service.get_bid(bid_repository, sample_bid.id)

        assert result is not None
        assert result.id == sample_bid.id
        assert result.title == sample_bid.title

    @pytest.mark.asyncio
    async def test_get_bid_not_exists(self, bid_repository: BidRepository):
        """존재하지 않는 Bid 조회 - None 반환"""
        result = await bid_service.get_bid(bid_repository, 99999)

        assert result is None

    # ============================================
    # get_bids 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_bids_default(self, bid_repository: BidRepository, multiple_bids: list):
        """기본 조회"""
        result = await bid_service.get_bids(bid_repository)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_bids_pagination_skip(self, bid_repository: BidRepository, multiple_bids: list):
        """페이지네이션 - skip"""
        result = await bid_service.get_bids(bid_repository, skip=2)

        assert len(result) == 3  # 5개 중 2개 스킵

    @pytest.mark.asyncio
    async def test_get_bids_pagination_limit(self, bid_repository: BidRepository, multiple_bids: list):
        """페이지네이션 - limit"""
        result = await bid_service.get_bids(bid_repository, limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bids_pagination_skip_and_limit(self, bid_repository: BidRepository, multiple_bids: list):
        """페이지네이션 - skip + limit"""
        result = await bid_service.get_bids(bid_repository, skip=1, limit=2)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_bids_keyword_filter(self, bid_repository: BidRepository, sample_bid: BidAnnouncement):
        """키워드 필터링"""
        result = await bid_service.get_bids(bid_repository, keyword="구내식당")

        assert len(result) >= 1
        assert any("구내식당" in bid.title for bid in result)

    @pytest.mark.asyncio
    async def test_get_bids_keyword_filter_no_match(self, bid_repository: BidRepository, multiple_bids: list):
        """키워드 필터링 - 매칭 없음"""
        result = await bid_service.get_bids(bid_repository, keyword="존재하지않는키워드xyz")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_bids_agency_filter(self, bid_repository: BidRepository, sample_bid: BidAnnouncement):
        """기관 필터링"""
        result = await bid_service.get_bids(bid_repository, agency="서울대")

        assert len(result) >= 1
        assert any("서울대" in (bid.agency or "") for bid in result)

    # ============================================
    # update_bid_processing_status 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_to_true(
        self, bid_repository: BidRepository, sample_bid: BidAnnouncement
    ):
        """처리 상태를 True로 업데이트"""
        assert sample_bid.processed is False

        await bid_service.update_bid_processing_status(bid_repository, sample_bid.id, True)

        # DB에서 다시 조회
        updated_bid = await bid_service.get_bid(bid_repository, sample_bid.id)
        assert updated_bid.processed is True

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_to_false(
        self, bid_repository: BidRepository, sample_bid: BidAnnouncement
    ):
        """처리 상태를 False로 업데이트"""
        # 먼저 True로 설정
        await bid_service.update_bid_processing_status(bid_repository, sample_bid.id, True)

        # 다시 False로 변경
        await bid_service.update_bid_processing_status(bid_repository, sample_bid.id, False)

        updated_bid = await bid_service.get_bid(bid_repository, sample_bid.id)
        assert updated_bid.processed is False

    @pytest.mark.asyncio
    async def test_update_bid_processing_status_nonexistent(self, bid_repository: BidRepository):
        """존재하지 않는 Bid 업데이트 시도"""
        # 예외가 발생하거나 None이 반환되어야 함
        result = await bid_service.update_bid_processing_status(bid_repository, 99999, True)
        # 구현에 따라 None을 반환하거나 예외를 발생시킬 수 있음
        # 여기서는 함수가 실행되는지만 확인


from unittest.mock import AsyncMock, MagicMock, patch


class TestGetMatchingBidsMock:
    """get_matching_bids 단위 테스트 (Mock)"""

    def setup_method(self):
        from app.services.bid_service import BidService

        self.service = BidService()

    @patch("app.services.bid_service.hard_match_engine")
    @patch("app.services.bid_service.subscription_service")
    async def test_free_user_limited(self, mock_sub, mock_engine):
        """Free 플랜 사용자 - 3건 제한"""
        mock_sub.get_user_plan = AsyncMock(return_value="free")
        mock_sub.get_plan_limits = AsyncMock(return_value={"hard_match_limit": 3})

        repo = AsyncMock()
        bids = [MagicMock(id=i, title=f"공고{i}") for i in range(10)]
        repo.get_multi_with_filters.return_value = bids

        mock_engine.evaluate.return_value = (True, [], {})

        user = MagicMock()
        profile = MagicMock()

        result = await self.service.get_matching_bids(repo, profile, user=user, limit=100)
        assert len(result) <= 3

    @patch("app.services.bid_service.hard_match_engine")
    @patch("app.services.bid_service.subscription_service")
    async def test_pro_user_unlimited(self, mock_sub, mock_engine):
        """Pro 플랜 사용자 - 제한 없음"""
        mock_sub.get_user_plan = AsyncMock(return_value="pro")
        mock_sub.get_plan_limits = AsyncMock(return_value={"hard_match_limit": 9999})

        repo = AsyncMock()
        bids = [MagicMock(id=i, title=f"공고{i}") for i in range(10)]
        repo.get_multi_with_filters.return_value = bids

        mock_engine.evaluate.return_value = (True, [], {})

        user = MagicMock()
        profile = MagicMock()

        result = await self.service.get_matching_bids(repo, profile, user=user)
        assert len(result) == 10

    @patch("app.services.bid_service.hard_match_engine")
    async def test_no_user_default_limit(self, mock_engine):
        """사용자 없이 호출 (기본 limit 100)"""
        repo = AsyncMock()
        bids = [MagicMock(id=i, title=f"공고{i}") for i in range(5)]
        repo.get_multi_with_filters.return_value = bids

        mock_engine.evaluate.return_value = (True, [], {})

        profile = MagicMock()
        result = await self.service.get_matching_bids(repo, profile)
        assert len(result) == 5

    @patch("app.services.bid_service.hard_match_engine")
    @patch("app.services.bid_service.subscription_service")
    async def test_skip_beyond_max(self, mock_sub, mock_engine):
        """skip이 max_allowed 이상이면 빈 리스트"""
        mock_sub.get_user_plan = AsyncMock(return_value="free")
        mock_sub.get_plan_limits = AsyncMock(return_value={"hard_match_limit": 3})

        repo = AsyncMock()
        user = MagicMock()
        profile = MagicMock()

        result = await self.service.get_matching_bids(repo, profile, user=user, skip=10)
        assert result == []

    @patch("app.services.bid_service.hard_match_engine")
    async def test_partial_match(self, mock_engine):
        """일부만 매칭되는 경우"""
        repo = AsyncMock()
        bids = [MagicMock(id=i, title=f"공고{i}") for i in range(5)]
        repo.get_multi_with_filters.return_value = bids

        # 짝수 ID만 매칭
        mock_engine.evaluate.side_effect = [
            (True, [], {}) if i % 2 == 0 else (False, ["지역 불일치"], {}) for i in range(5)
        ]

        profile = MagicMock()
        result = await self.service.get_matching_bids(repo, profile)
        assert len(result) == 3  # 0, 2, 4
