"""
Taskiq Background Tasks 단위 테스트
- crawl_g2b_bids (mock DB + crawler)
- send_morning_digest (mock DB)
- process_bid_analysis (mock DB + RAG)
- process_subscription_renewals (mock DB + payment)
- process_subscription_expirations (mock DB)
- send_subscription_email (mock DB + email)

NOTE: taskiq는 설치되어 있지 않으므로 sys.modules mock 필요
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_taskiq_and_import():
    """taskiq 의존성을 mock하고 task 함수들을 import"""
    mock_broker = MagicMock()
    mock_broker.task = lambda **kw: lambda f: f  # passthrough decorator

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


# Import the module once at module level
_tasks = _mock_taskiq_and_import()


# ============================================
# crawl_g2b_bids
# ============================================


class TestCrawlG2BBids:

    @pytest.mark.asyncio
    async def test_no_announcements(self):
        """크롤링 결과가 없으면 빠르게 반환"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_crawler = MagicMock()
        mock_crawler.DEFAULT_EXCLUDE_KEYWORDS = ["폐기물"]
        mock_crawler.INCLUDE_KEYWORDS_CONCESSION = ["구내식당"]
        mock_crawler.INCLUDE_KEYWORDS_FLOWER = ["화환"]
        mock_crawler.fetch_new_announcements = AsyncMock(return_value=[])

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "G2BCrawlerService", return_value=mock_crawler):
                await _tasks.crawl_g2b_bids()

        mock_crawler.fetch_new_announcements.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_duplicate_url_skip(self):
        """중복 URL은 건너뛰기"""
        mock_session = AsyncMock()

        exclude_result = MagicMock()
        exclude_result.scalars.return_value.all.return_value = []
        include_result = MagicMock()
        include_result.scalars.return_value.all.return_value = []
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = []
        existing_urls_result = MagicMock()
        existing_urls_result.scalars.return_value.all.return_value = ["https://dup.com"]

        mock_session.execute = AsyncMock(
            side_effect=[exclude_result, include_result, users_result, existing_urls_result]
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_crawler = MagicMock()
        mock_crawler.DEFAULT_EXCLUDE_KEYWORDS = []
        mock_crawler.INCLUDE_KEYWORDS_CONCESSION = ["구내식당"]
        mock_crawler.INCLUDE_KEYWORDS_FLOWER = []
        mock_crawler.fetch_new_announcements = AsyncMock(return_value=[
            {"url": "https://dup.com", "title": "중복"}
        ])

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "G2BCrawlerService", return_value=mock_crawler):
                await _tasks.crawl_g2b_bids()

        mock_session.add.assert_not_called()



# ============================================
# send_morning_digest
# ============================================


class TestSendMorningDigest:

    @pytest.mark.asyncio
    async def test_no_announcements(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            await _tasks.send_morning_digest()

    @pytest.mark.asyncio
    async def test_with_announcements(self):
        mock_bid = MagicMock()
        mock_bid.title = "테스트"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_bid]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            await _tasks.send_morning_digest()


# ============================================
# process_bid_analysis
# ============================================


class TestProcessBidAnalysis:

    @pytest.mark.asyncio
    async def test_bid_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            await _tasks.process_bid_analysis(9999)

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_success(self):
        mock_bid = MagicMock()
        mock_bid.title = "공고 제목"
        mock_bid.content = "공고 내용"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_bid
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        mock_rag = MagicMock()
        mock_rag.analyze_bid = AsyncMock(return_value={
            "summary": "AI 요약",
            "keywords": ["kw1"],
            "region_code": "11",
            "license_requirements": "건축",
            "min_performance": 100000000,
        })

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "RAGService", return_value=mock_rag):
                await _tasks.process_bid_analysis(1)

        assert mock_bid.ai_summary == "AI 요약"
        assert mock_bid.processed is True
        mock_session.commit.assert_awaited_once()


# ============================================
# process_subscription_renewals
# ============================================


class TestProcessSubscriptionRenewals:

    @pytest.mark.asyncio
    async def test_no_subscriptions(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            await _tasks.process_subscription_renewals()

    @pytest.mark.asyncio
    async def test_free_plan_skip(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_sub = MagicMock()
        mock_sub.user_id = 1
        mock_sub.plan_name = "free"
        mock_sub.billing_key = "bk_test"
        mock_sub.user = mock_user

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_sub]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "payment_service") as mock_ps:
                mock_ps.get_plan_amount.return_value = 0
                await _tasks.process_subscription_renewals()

        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_renewal_failure(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_sub = MagicMock()
        mock_sub.user_id = 1
        mock_sub.plan_name = "basic"
        mock_sub.billing_key = "bk_test"
        mock_sub.user = mock_user

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_sub]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "payment_service") as mock_ps:
                mock_ps.get_plan_amount.return_value = 10000
                mock_ps.generate_order_id.return_value = "BIZ-1-BASIC-test"
                mock_ps.generate_idempotency_key.return_value = "key-123"
                mock_ps.charge_billing_key = AsyncMock(side_effect=Exception("결제 실패"))
                with patch.object(_tasks, "subscription_service") as mock_ss:
                    mock_ss.handle_payment_failure = AsyncMock()
                    with patch.object(_tasks, "email_service") as mock_es:
                        mock_es.is_configured.return_value = False
                        await _tasks.process_subscription_renewals()

        mock_session.rollback.assert_awaited()
        mock_ss.handle_payment_failure.assert_awaited_once()


# ============================================
# process_subscription_expirations
# ============================================


class TestProcessSubscriptionExpirations:

    @pytest.mark.asyncio
    async def test_no_expirations(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            await _tasks.process_subscription_expirations()

    @pytest.mark.asyncio
    async def test_cancelled_expiration(self):
        mock_sub = MagicMock()
        mock_sub.user_id = 1

        mock_session = AsyncMock()
        cancelled_result = MagicMock()
        cancelled_result.scalars.return_value.all.return_value = [mock_sub]
        past_due_result = MagicMock()
        past_due_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[cancelled_result, past_due_result])
        mock_session.commit = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "subscription_service") as mock_ss:
                mock_ss.expire_subscription = AsyncMock()
                await _tasks.process_subscription_expirations()

        mock_ss.expire_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_past_due_expiration(self):
        mock_sub = MagicMock()
        mock_sub.user_id = 2

        mock_session = AsyncMock()
        cancelled_result = MagicMock()
        cancelled_result.scalars.return_value.all.return_value = []
        past_due_result = MagicMock()
        past_due_result.scalars.return_value.all.return_value = [mock_sub]

        mock_session.execute = AsyncMock(side_effect=[cancelled_result, past_due_result])
        mock_session.commit = AsyncMock()

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
            with patch.object(_tasks, "subscription_service") as mock_ss:
                mock_ss.expire_subscription = AsyncMock()
                await _tasks.process_subscription_expirations()

        mock_ss.expire_subscription.assert_awaited_once()


# ============================================
# send_subscription_email
# ============================================


class TestSendSubscriptionEmail:

    @pytest.mark.asyncio
    async def test_not_configured(self):
        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = False
            await _tasks.send_subscription_email(1, "renewal_success", "basic", 10000)

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(999, "renewal_success", "basic")

    @pytest.mark.asyncio
    async def test_renewal_success(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=True)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "renewal_success", "basic", 10000)

        mock_es.send_email.assert_awaited_once()
        assert "BASIC" in mock_es.send_email.call_args.kwargs.get("subject", "")

    @pytest.mark.asyncio
    async def test_payment_failed(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=True)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "payment_failed", "pro", 30000)

        assert "실패" in mock_es.send_email.call_args.kwargs.get("subject", "")

    @pytest.mark.asyncio
    async def test_expiring(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=True)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "subscription_expiring", "basic")

        assert "만료" in mock_es.send_email.call_args.kwargs.get("subject", "")

    @pytest.mark.asyncio
    async def test_cancelled(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=True)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "subscription_cancelled", "pro")

        assert "해지" in mock_es.send_email.call_args.kwargs.get("subject", "")

    @pytest.mark.asyncio
    async def test_unknown_type(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=True)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "unknown_type", "basic")

        mock_es.send_email.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_email_send_failure(self):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_maker = AsyncMock()
        mock_session_maker.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.__aexit__ = AsyncMock(return_value=None)

        with patch.object(_tasks, "email_service") as mock_es:
            mock_es.is_configured.return_value = True
            mock_es.send_email = AsyncMock(return_value=False)
            with patch.object(_tasks, "AsyncSessionLocal", return_value=mock_session_maker):
                await _tasks.send_subscription_email(1, "renewal_success", "basic", 10000)

        mock_es.send_email.assert_awaited_once()
