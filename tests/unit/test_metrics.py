"""
Prometheus 메트릭 단위 테스트
"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest
from prometheus_client import REGISTRY

from app.core.metrics import (APP_INFO, CACHE_HITS_TOTAL, CACHE_MISSES_TOTAL,
                              CELERY_TASKS_TOTAL,
                              CRAWLER_ANNOUNCEMENTS_COLLECTED,
                              CRAWLER_RUNS_TOTAL,
                              HTTP_REQUEST_DURATION_SECONDS,
                              HTTP_REQUESTS_IN_PROGRESS, HTTP_REQUESTS_TOTAL,
                              NOTIFICATIONS_SENT_TOTAL, init_app_info,
                              record_announcement_collected, record_cache_hit,
                              record_cache_miss, record_celery_task,
                              record_notification_sent, track_crawler_run,
                              track_request_metrics)


class TestHTTPMetrics:
    """HTTP 요청 메트릭 테스트"""

    def test_http_requests_total_increment(self):
        """HTTP 요청 카운터 증가"""
        before = HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()

        HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status_code="200"
        ).inc()

        after = HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status_code="200"
        )._value.get()

        assert after == before + 1

    def test_http_request_duration_observe(self):
        """HTTP 요청 시간 히스토그램 기록"""
        # 0.1초 기록
        HTTP_REQUEST_DURATION_SECONDS.labels(method="GET", endpoint="/test").observe(
            0.1
        )

        # 에러 없이 실행되면 성공

    def test_http_requests_in_progress_gauge(self):
        """진행 중인 요청 게이지"""
        gauge = HTTP_REQUESTS_IN_PROGRESS.labels(method="POST", endpoint="/api/test")

        gauge.inc()
        assert gauge._value.get() >= 1

        gauge.dec()
        # 감소 확인


class TestTrackRequestMetricsDecorator:
    """track_request_metrics 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """성공적인 요청 추적"""

        @track_request_metrics("GET", "/test/decorated")
        async def mock_endpoint():
            await asyncio.sleep(0.01)
            return {"status": "ok"}

        result = await mock_endpoint()

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_failed_request(self):
        """실패한 요청 추적"""

        @track_request_metrics("POST", "/test/fail")
        async def mock_failing_endpoint():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await mock_failing_endpoint()


class TestCrawlerMetrics:
    """크롤러 메트릭 테스트"""

    def test_crawler_runs_total(self):
        """크롤링 실행 카운터"""
        before = CRAWLER_RUNS_TOTAL.labels(source="G2B", status="success")._value.get()

        CRAWLER_RUNS_TOTAL.labels(source="G2B", status="success").inc()

        after = CRAWLER_RUNS_TOTAL.labels(source="G2B", status="success")._value.get()

        assert after == before + 1

    def test_record_announcement_collected(self):
        """공고 수집 기록"""
        before = CRAWLER_ANNOUNCEMENTS_COLLECTED.labels(
            source="Onbid", importance_score="3"
        )._value.get()

        record_announcement_collected(source="Onbid", importance_score=3)

        after = CRAWLER_ANNOUNCEMENTS_COLLECTED.labels(
            source="Onbid", importance_score="3"
        )._value.get()

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_track_crawler_run_decorator(self):
        """track_crawler_run 데코레이터"""

        @track_crawler_run("TestSource")
        async def mock_crawler():
            await asyncio.sleep(0.01)
            return [{"title": "Test"}]

        result = await mock_crawler()

        assert len(result) == 1


class TestCacheMetrics:
    """캐시 메트릭 테스트"""

    def test_record_cache_hit(self):
        """캐시 히트 기록"""
        before = CACHE_HITS_TOTAL.labels(cache_type="redis")._value.get()

        record_cache_hit("redis")

        after = CACHE_HITS_TOTAL.labels(cache_type="redis")._value.get()

        assert after == before + 1

    def test_record_cache_miss(self):
        """캐시 미스 기록"""
        before = CACHE_MISSES_TOTAL.labels(cache_type="local")._value.get()

        record_cache_miss("local")

        after = CACHE_MISSES_TOTAL.labels(cache_type="local")._value.get()

        assert after == before + 1


class TestNotificationMetrics:
    """알림 메트릭 테스트"""

    def test_record_notification_sent_success(self):
        """알림 발송 성공 기록"""
        before = NOTIFICATIONS_SENT_TOTAL.labels(
            channel="slack", type="important", status="success"
        )._value.get()

        record_notification_sent("slack", "important", success=True)

        after = NOTIFICATIONS_SENT_TOTAL.labels(
            channel="slack", type="important", status="success"
        )._value.get()

        assert after == before + 1

    def test_record_notification_sent_failure(self):
        """알림 발송 실패 기록"""
        before = NOTIFICATIONS_SENT_TOTAL.labels(
            channel="slack", type="alert", status="failure"
        )._value.get()

        record_notification_sent("slack", "alert", success=False)

        after = NOTIFICATIONS_SENT_TOTAL.labels(
            channel="slack", type="alert", status="failure"
        )._value.get()

        assert after == before + 1


class TestCeleryMetrics:
    """Celery 작업 메트릭 테스트"""

    def test_record_celery_task(self):
        """Celery 작업 기록"""
        before = CELERY_TASKS_TOTAL.labels(
            task_name="crawl_g2b", status="success"
        )._value.get()

        record_celery_task("crawl_g2b", "success", duration=5.5)

        after = CELERY_TASKS_TOTAL.labels(
            task_name="crawl_g2b", status="success"
        )._value.get()

        assert after == before + 1


class TestAppInfo:
    """앱 정보 메트릭 테스트"""

    def test_init_app_info(self):
        """앱 정보 초기화"""
        init_app_info(version="2.0.0")

        # Info 메트릭은 _value 대신 다른 방식으로 확인
        # 에러 없이 실행되면 성공
