"""
G2BCrawlerService 단위 테스트
- _parse_api_response
- _should_notify (키워드 필터링)
- calculate_importance_score
- _parse_datetime
- fetch_new_announcements (mock httpx)
- fetch_opening_results (mock httpx)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.crawler_service import G2BCrawlerService


@pytest.fixture
def crawler():
    return G2BCrawlerService()


# ============================================
# _parse_datetime
# ============================================


def test_parse_datetime_valid(crawler):
    result = crawler._parse_datetime("202601221200")
    assert result is not None
    assert result.year == 2026
    assert result.month == 1

def test_parse_datetime_valid_full(crawler):
    result = crawler._parse_datetime("202601151030")
    assert result == datetime(2026, 1, 15, 10, 30)

def test_parse_datetime_none(crawler):
    assert crawler._parse_datetime(None) is None

def test_parse_datetime_empty(crawler):
    assert crawler._parse_datetime("") is None

def test_parse_datetime_invalid(crawler):
    assert crawler._parse_datetime("invalid") is None

def test_parse_datetime_wrong_format(crawler):
    assert crawler._parse_datetime("2026-01-15") is None

def test_parse_datetime_partial(crawler):
    assert crawler._parse_datetime("20260115") is None


# ============================================
# _parse_api_response
# ============================================


class TestParseApiResponse:

    def test_valid_response(self, crawler):
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "구내식당 위탁운영",
                            "bidNtceDtl": "상세 내용",
                            "ntceInsttNm": "서울시청",
                            "bidNtceDt": "202601151000",
                            "bidClseDt": "202601221800",
                            "bidNtceUrl": "https://g2b.go.kr/bid/1",
                            "presmptPrce": "150000000",
                        }
                    ]
                }
            }
        }
        result = crawler._parse_api_response(data)
        assert len(result) == 1
        assert result[0]["title"] == "구내식당 위탁운영"
        assert result[0]["agency"] == "서울시청"
        assert result[0]["estimated_price"] == 150000000.0
        assert result[0]["source"] == "G2B"

    def test_empty_items(self, crawler):
        data = {"response": {"body": {"items": []}}}
        assert crawler._parse_api_response(data) == []

    def test_missing_body(self, crawler):
        data = {"response": {}}
        assert crawler._parse_api_response(data) == []

    def test_missing_date_uses_now(self, crawler):
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "테스트",
                            "bidNtceDtl": "내용",
                            "ntceInsttNm": "기관",
                            "bidNtceDt": None,
                            "bidClseDt": None,
                            "bidNtceUrl": "http://test",
                            "presmptPrce": "0",
                        }
                    ]
                }
            }
        }
        result = crawler._parse_api_response(data)
        assert len(result) == 1
        assert result[0]["posted_at"] is not None

    def test_null_price_defaults_zero(self, crawler):
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "테스트",
                            "bidNtceDtl": "",
                            "ntceInsttNm": "기관",
                            "bidNtceDt": "202601151000",
                            "bidClseDt": None,
                            "bidNtceUrl": "",
                            "presmptPrce": None,
                        }
                    ]
                }
            }
        }
        result = crawler._parse_api_response(data)
        assert result[0]["estimated_price"] == 0.0

    def test_empty_content_defaults(self, crawler):
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "제목",
                            "bidNtceDtl": "",
                            "ntceInsttNm": "",
                            "bidNtceDt": "202601151000",
                            "bidClseDt": None,
                            "bidNtceUrl": "",
                            "presmptPrce": "0",
                        }
                    ]
                }
            }
        }
        result = crawler._parse_api_response(data)
        assert result[0]["content"] == "내용 없음"


# ============================================
# _should_notify (키워드 필터링)
# ============================================


def test_should_notify_with_valid_keywords(crawler, sample_announcement_data):
    result = crawler._should_notify(sample_announcement_data)
    assert result is True

def test_should_notify_with_exclude_keywords(crawler):
    announcement = {"title": "폐기물 처리 용역", "content": "폐기물 수거 및 처리"}
    result = crawler._should_notify(announcement)
    assert result is False

def test_should_notify_include_keyword_match(crawler):
    announcement = {"title": "구내식당 위탁운영 입찰", "content": "식당 관련 공고"}
    result = crawler._should_notify(
        announcement,
        exclude_keywords=["폐기물"],
        include_keywords=["구내식당", "위탁운영"],
    )
    assert result is True
    assert "구내식당" in announcement["keywords_matched"]

def test_should_notify_exclude_blocks(crawler):
    announcement = {"title": "폐기물 처리 위탁운영", "content": ""}
    result = crawler._should_notify(
        announcement,
        exclude_keywords=["폐기물"],
        include_keywords=["위탁운영"],
    )
    assert result is False

def test_should_notify_no_match(crawler):
    announcement = {"title": "도로 보수 공사", "content": "도로 관련"}
    result = crawler._should_notify(
        announcement,
        exclude_keywords=["폐기물"],
        include_keywords=["구내식당"],
    )
    assert result is False

def test_should_notify_content_match(crawler):
    announcement = {"title": "일반 공고", "content": "화환 납품 관련 공고입니다"}
    result = crawler._should_notify(
        announcement,
        exclude_keywords=[],
        include_keywords=["화환"],
    )
    assert result is True

def test_should_notify_default_keywords(crawler):
    announcement = {"title": "구내식당 위탁운영", "content": ""}
    result = crawler._should_notify(announcement)
    assert result is True


# ============================================
# calculate_importance_score
# ============================================


def test_importance_score_high(crawler, sample_announcement_data):
    sample_announcement_data["title"] = "서울대병원 구내식당 위탁운영"
    sample_announcement_data["estimated_price"] = 150000000
    sample_announcement_data["keywords_matched"] = ["구내식당", "위탁운영", "장례식장"]
    score = crawler.calculate_importance_score(sample_announcement_data)
    assert score >= 2

def test_importance_score_low(crawler, sample_announcement_data):
    sample_announcement_data["title"] = "일반 물품 구매"
    sample_announcement_data["estimated_price"] = 1000000
    sample_announcement_data["keywords_matched"] = ["물품"]
    score = crawler.calculate_importance_score(sample_announcement_data)
    assert score == 1

def test_importance_high_price(crawler):
    announcement = {
        "title": "일반 공고",
        "keywords_matched": [],
        "estimated_price": 200000000,
    }
    assert crawler.calculate_importance_score(announcement) >= 2

def test_importance_many_keywords(crawler):
    announcement = {
        "title": "일반 공고",
        "keywords_matched": ["kw1", "kw2", "kw3"],
        "estimated_price": 10000000,
    }
    assert crawler.calculate_importance_score(announcement) >= 2

def test_importance_max_capped(crawler):
    announcement = {
        "title": "구내식당 위탁운영",
        "keywords_matched": ["kw1", "kw2", "kw3"],
        "estimated_price": 500000000,
    }
    assert crawler.calculate_importance_score(announcement) == 3

def test_importance_no_keywords_key(crawler):
    announcement = {"title": "일반 공고", "estimated_price": 0}
    assert crawler.calculate_importance_score(announcement) == 1


# ============================================
# fetch_new_announcements (mock httpx)
# ============================================


class TestFetchNewAnnouncements:

    @pytest.mark.asyncio
    async def test_successful_fetch(self, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "구내식당 위탁운영",
                            "bidNtceDtl": "내용",
                            "ntceInsttNm": "서울시청",
                            "bidNtceDt": "202601151000",
                            "bidClseDt": "202601221800",
                            "bidNtceUrl": "https://g2b.go.kr/bid/1",
                            "presmptPrce": "150000000",
                        }
                    ]
                },
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_new_announcements(
                include_keywords=["구내식당"],
                exclude_keywords=["폐기물"],
            )

        assert len(result) == 1
        assert result[0]["title"] == "구내식당 위탁운영"

    @pytest.mark.asyncio
    async def test_api_error_returns_empty(self, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "99", "resultMsg": "SERVICE ERROR"},
                "body": {"items": []},
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_new_announcements()

        assert result == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, crawler):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_new_announcements()

        assert result == []

    @pytest.mark.asyncio
    async def test_with_from_date(self, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": []},
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_new_announcements(
                from_date=datetime(2026, 1, 1)
            )
        assert result == []


# ============================================
# fetch_opening_results (mock httpx)
# ============================================


class TestFetchOpeningResults:

    @pytest.mark.asyncio
    async def test_successful_fetch(self, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": [
                        {
                            "bidNtceNo": "20260115001",
                            "bidNtceNm": "개찰 결과",
                            "ntceInsttNm": "서울시청",
                            "sucsfutlEntrpsNm": "낙찰업체",
                            "sucsfutlAmt": "100000000",
                            "baseAmt": "95000000",
                            "presmptPrce": "120000000",
                            "bidEntrpsCnt": "5",
                            "opengDt": "202601151400",
                        }
                    ]
                },
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_opening_results()

        assert len(result) == 1
        assert result[0]["winning_company"] == "낙찰업체"
        assert result[0]["winning_price"] == 100000000.0
        assert result[0]["participant_count"] == 5

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, crawler):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("API Error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_opening_results()

        assert result == []

    @pytest.mark.asyncio
    async def test_api_business_error(self, crawler):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "99"},
                "body": {"items": []},
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await crawler.fetch_opening_results()

        assert result == []


# ============================================
# close
# ============================================


@pytest.mark.asyncio
async def test_close(crawler):
    await crawler.close()
