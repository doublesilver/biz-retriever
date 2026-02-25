"""
DI Factory 함수 테스트
- get_bid_repository
- get_crawler_service
- get_rag_service
- get_notification_service
"""

from unittest.mock import MagicMock

from app.api.deps import (
    get_bid_repository,
    get_crawler_service,
    get_notification_service,
    get_rag_service,
)


class TestDIFactories:
    def test_get_bid_repository(self):
        mock_session = MagicMock()
        repo = get_bid_repository(mock_session)
        assert repo is not None
        assert repo.session == mock_session

    def test_get_crawler_service(self):
        svc = get_crawler_service()
        assert svc is not None

    def test_get_rag_service(self):
        svc = get_rag_service()
        assert svc is not None

    def test_get_notification_service(self):
        svc = get_notification_service()
        assert svc is not None
