"""
Prometheus 메트릭 데코레이터 확장 테스트
- track_db_query
- track_ai_analysis
- track_crawler_run (실패 케이스)
"""

import asyncio
import pytest

from app.core.metrics import (
    DB_QUERIES_TOTAL,
    DB_QUERY_DURATION_SECONDS,
    AI_ANALYSIS_TOTAL,
    AI_ANALYSIS_DURATION_SECONDS,
    CRAWLER_RUNS_TOTAL,
    track_db_query,
    track_ai_analysis,
    track_crawler_run,
)


class TestTrackDbQuery:
    """track_db_query 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_successful_query(self):
        """성공적인 DB 쿼리 추적"""
        before = DB_QUERIES_TOTAL.labels(
            operation="SELECT", table="bids"
        )._value.get()

        @track_db_query("SELECT", "bids")
        async def mock_query():
            await asyncio.sleep(0.01)
            return [{"id": 1}]

        result = await mock_query()
        assert result == [{"id": 1}]

        after = DB_QUERIES_TOTAL.labels(
            operation="SELECT", table="bids"
        )._value.get()
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_query_duration_recorded(self):
        """쿼리 시간 히스토그램 기록"""

        @track_db_query("INSERT", "users")
        async def mock_insert():
            await asyncio.sleep(0.01)
            return True

        result = await mock_insert()
        assert result is True


class TestTrackAiAnalysis:
    """track_ai_analysis 데코레이터 테스트"""

    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        """성공적인 AI 분석 추적"""
        before = AI_ANALYSIS_TOTAL.labels(
            provider="gemini", status="success"
        )._value.get()

        @track_ai_analysis("gemini")
        async def mock_analysis():
            await asyncio.sleep(0.01)
            return {"score": 0.85}

        result = await mock_analysis()
        assert result["score"] == 0.85

        after = AI_ANALYSIS_TOTAL.labels(
            provider="gemini", status="success"
        )._value.get()
        assert after == before + 1

    @pytest.mark.asyncio
    async def test_failed_analysis(self):
        """실패한 AI 분석 추적"""
        before_fail = AI_ANALYSIS_TOTAL.labels(
            provider="openai", status="failure"
        )._value.get()

        @track_ai_analysis("openai")
        async def mock_failing_analysis():
            raise RuntimeError("API limit exceeded")

        with pytest.raises(RuntimeError):
            await mock_failing_analysis()

        after_fail = AI_ANALYSIS_TOTAL.labels(
            provider="openai", status="failure"
        )._value.get()
        assert after_fail == before_fail + 1


class TestTrackCrawlerRunFailure:
    """track_crawler_run 실패 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_crawler_failure(self):
        """크롤링 실패 시 failure 카운터 증가"""
        before = CRAWLER_RUNS_TOTAL.labels(
            source="FailSource", status="failure"
        )._value.get()

        @track_crawler_run("FailSource")
        async def mock_failing_crawler():
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            await mock_failing_crawler()

        after = CRAWLER_RUNS_TOTAL.labels(
            source="FailSource", status="failure"
        )._value.get()
        assert after == before + 1
