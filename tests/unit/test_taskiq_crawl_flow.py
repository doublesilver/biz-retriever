"""
Taskiq crawl_g2b_bids 확장 테스트 — 새 공고 저장 + 사용자 키워드 매칭 + WebSocket 브로드캐스트 흐름
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _get_tasks():
    """taskiq 의존성 mock 후 import"""
    mock_broker = MagicMock()
    mock_broker.task = lambda **kw: lambda f: f

    mock_modules = {
        "taskiq": MagicMock(),
        "taskiq.schedule_sources": MagicMock(),
        "taskiq_redis": MagicMock(ListQueueBroker=lambda **kw: mock_broker),
    }

    with patch.dict(sys.modules, mock_modules):
        with patch("app.worker.taskiq_app.broker", mock_broker):
            import importlib

            import app.worker.taskiq_tasks as module

            importlib.reload(module)
            return module


_tasks = _get_tasks()


class TestCrawlG2BNewAnnouncementFlow:
    """새 공고 저장 및 알림 흐름 테스트"""

    @pytest.mark.asyncio
    async def test_new_announcement_saved_and_broadcast(self):
        """새 공고가 저장되고 WebSocket 브로드캐스트됨"""
        mock_session = AsyncMock()

        # DB 조회 결과들
        exclude_result = MagicMock()
        exclude_result.scalars.return_value.all.return_value = []
        include_result = MagicMock()
        include_result.scalars.return_value.all.return_value = ["구내식당"]
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = []
        existing_urls_result = MagicMock()
        existing_urls_result.scalars.return_value.all.return_value = []  # no duplicates

        mock_session.execute = AsyncMock(
            side_effect=[exclude_result, include_result, users_result, existing_urls_result]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        # refresh는 새 공고 객체의 id를 설정
        async def fake_refresh(obj):
            obj.id = 1
            obj.title = "구내식당 임대"
            obj.agency = "테스트기관"

        mock_session.refresh = AsyncMock(side_effect=fake_refresh)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_crawler = MagicMock()
        mock_crawler.DEFAULT_EXCLUDE_KEYWORDS = []
        mock_crawler.INCLUDE_KEYWORDS_CONCESSION = ["구내식당"]
        mock_crawler.INCLUDE_KEYWORDS_FLOWER = []
        mock_crawler.calculate_importance_score.return_value = 1
        mock_crawler.fetch_new_announcements = AsyncMock(
            return_value=[
                {
                    "url": "https://new.com/1",
                    "title": "구내식당 임대",
                    "content": "식당 운영",
                    "agency": "테스트기관",
                    "posted_at": "2026-01-20",
                    "source": "G2B",
                    "deadline": None,
                    "estimated_price": 0,
                    "keywords_matched": ["구내식당"],
                }
            ]
        )

        mock_manager = AsyncMock()

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "G2BCrawlerService", return_value=mock_crawler):
                with patch.object(_tasks, "manager", mock_manager):
                    with patch.object(_tasks, "process_bid_analysis", MagicMock(kiq=AsyncMock())):
                        await _tasks.crawl_g2b_bids()

        # 공고가 저장되었는지 확인
        mock_session.add.assert_called()
        mock_session.commit.assert_awaited()
        # WebSocket 브로드캐스트 호출
        mock_manager.broadcast.assert_awaited()

    @pytest.mark.asyncio
    async def test_high_importance_triggers_analysis(self):
        """중요도 2 이상인 공고는 AI 분석 트리거"""
        mock_session = AsyncMock()

        exclude_result = MagicMock()
        exclude_result.scalars.return_value.all.return_value = []
        include_result = MagicMock()
        include_result.scalars.return_value.all.return_value = []
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = []
        existing_urls_result = MagicMock()
        existing_urls_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[exclude_result, include_result, users_result, existing_urls_result]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        async def fake_refresh(obj):
            obj.id = 42
            obj.title = "중요 공고"
            obj.agency = "기관"

        mock_session.refresh = AsyncMock(side_effect=fake_refresh)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_crawler = MagicMock()
        mock_crawler.DEFAULT_EXCLUDE_KEYWORDS = []
        mock_crawler.INCLUDE_KEYWORDS_CONCESSION = ["구내식당"]
        mock_crawler.INCLUDE_KEYWORDS_FLOWER = []
        mock_crawler.calculate_importance_score.return_value = 3  # 높은 중요도

        mock_crawler.fetch_new_announcements = AsyncMock(
            return_value=[
                {
                    "url": "https://important.com/1",
                    "title": "중요 공고",
                    "content": "",
                    "agency": "기관",
                    "posted_at": "2026-01-20",
                    "source": "G2B",
                    "deadline": None,
                    "estimated_price": 0,
                    "keywords_matched": [],
                }
            ]
        )

        mock_process = MagicMock()
        mock_process.kiq = AsyncMock()

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "G2BCrawlerService", return_value=mock_crawler):
                with patch.object(_tasks, "manager", AsyncMock()):
                    with patch.object(_tasks, "process_bid_analysis", mock_process):
                        await _tasks.crawl_g2b_bids()

        mock_process.kiq.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_user_keyword_notification(self):
        """사용자 키워드 매칭 시 알림 전송"""
        mock_session = AsyncMock()

        mock_keyword = MagicMock()
        mock_keyword.keyword = "구내식당"
        mock_keyword.is_active = True
        mock_keyword.category = "include"

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.keywords = [mock_keyword]

        exclude_result = MagicMock()
        exclude_result.scalars.return_value.all.return_value = []
        include_result = MagicMock()
        include_result.scalars.return_value.all.return_value = []
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]
        existing_urls_result = MagicMock()
        existing_urls_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[exclude_result, include_result, users_result, existing_urls_result]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        async def fake_refresh(obj):
            obj.id = 10
            obj.title = "구내식당 위탁운영"
            obj.content = "식당 운영"
            obj.agency = "기관"

        mock_session.refresh = AsyncMock(side_effect=fake_refresh)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_crawler = MagicMock()
        mock_crawler.DEFAULT_EXCLUDE_KEYWORDS = []
        mock_crawler.INCLUDE_KEYWORDS_CONCESSION = ["구내식당"]
        mock_crawler.INCLUDE_KEYWORDS_FLOWER = []
        mock_crawler.calculate_importance_score.return_value = 1

        mock_crawler.fetch_new_announcements = AsyncMock(
            return_value=[
                {
                    "url": "https://new.com/2",
                    "title": "구내식당 위탁운영",
                    "content": "식당 운영",
                    "agency": "기관",
                    "posted_at": "2026-01-20",
                    "source": "G2B",
                    "deadline": None,
                    "estimated_price": 0,
                    "keywords_matched": ["구내식당"],
                }
            ]
        )

        mock_notify = AsyncMock()

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "G2BCrawlerService", return_value=mock_crawler):
                with patch.object(_tasks, "manager", AsyncMock()):
                    with patch.object(_tasks, "process_bid_analysis", MagicMock(kiq=AsyncMock())):
                        with patch.object(_tasks.NotificationService, "notify_bid_match", mock_notify):
                            await _tasks.crawl_g2b_bids()

        mock_notify.assert_awaited()
