"""
BidService 확장 테스트
- create_bid with processed=True
"""

from unittest.mock import AsyncMock, MagicMock

from app.services.bid_service import BidService


class TestBidServiceCreateProcessed:
    async def test_create_bid_processed_true(self):
        """processed=True일 때 추가 commit"""
        svc = BidService()

        mock_bid = MagicMock()
        mock_repo = MagicMock()
        mock_repo.create = AsyncMock(return_value=mock_bid)
        mock_repo.session.commit = AsyncMock()
        mock_repo.session.refresh = AsyncMock()

        result = await svc.create_bid(mock_repo, MagicMock(), processed=True)

        assert result.processed is True
        mock_repo.session.commit.assert_awaited_once()
        mock_repo.session.refresh.assert_awaited_once()
