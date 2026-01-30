"""
크롤러 서비스 단위 테스트
"""

import pytest

from app.services.crawler_service import G2BCrawlerService


@pytest.fixture
def crawler():
    return G2BCrawlerService()


def test_importance_score_high(crawler, sample_announcement_data):
    """중요도 점수 계산 - 높은 점수"""
    sample_announcement_data["title"] = "서울대병원 구내식당 위탁운영"
    sample_announcement_data["estimated_price"] = 150000000
    sample_announcement_data["keywords_matched"] = ["구내식당", "위탁운영", "장례식장"]

    score = crawler.calculate_importance_score(sample_announcement_data)
    assert score >= 2


def test_importance_score_low(crawler, sample_announcement_data):
    """중요도 점수 계산 - 낮은 점수"""
    sample_announcement_data["title"] = "일반 물품 구매"
    sample_announcement_data["estimated_price"] = 1000000
    sample_announcement_data["keywords_matched"] = ["물품"]

    score = crawler.calculate_importance_score(sample_announcement_data)
    assert score == 1


def test_should_notify_with_valid_keywords(crawler, sample_announcement_data):
    """알림 대상 판단 - 유효한 키워드"""
    result = crawler._should_notify(sample_announcement_data)
    assert result == True


def test_should_notify_with_exclude_keywords(crawler):
    """알림 대상 판단 - 제외 키워드"""
    announcement = {
        "title": "폐기물 처리 용역",
        "content": "폐기물 수거 및 처리",
        "keywords_matched": [],
    }
    result = crawler._should_notify(announcement)
    assert result == False


def test_parse_datetime_valid(crawler):
    """날짜 파싱 - 정상 케이스"""
    date_str = "202601221200"
    result = crawler._parse_datetime(date_str)
    assert result is not None
    assert result.year == 2026
    assert result.month == 1


def test_parse_datetime_invalid(crawler):
    """날짜 파싱 - 비정상 케이스"""
    result = crawler._parse_datetime("invalid")
    assert result is None


def test_parse_datetime_none(crawler):
    """날짜 파싱 - None 입력"""
    result = crawler._parse_datetime(None)
    assert result is None
