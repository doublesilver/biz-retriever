"""
OnbidCrawlerService 확장 단위 테스트
- _parse_deadline
- _parse_price
- _should_include
- _calculate_importance
- _parse_row
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.services.onbid_crawler import OnbidCrawlerService


@pytest.fixture
def service():
    return OnbidCrawlerService()


class TestParseDeadline:
    """마감일 파싱 테스트"""

    def test_valid_range(self, service):
        """유효한 기간 텍스트"""
        result = service._parse_deadline("2026-01-20 ~ 2026-01-25")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 25

    def test_no_tilde(self, service):
        """~ 없는 텍스트"""
        result = service._parse_deadline("2026-01-20")
        assert result is None

    def test_empty_string(self, service):
        """빈 문자열"""
        result = service._parse_deadline("")
        assert result is None

    def test_invalid_date(self, service):
        """유효하지 않은 날짜"""
        result = service._parse_deadline("2026-99-99 ~ 2026-13-45")
        assert result is None


class TestParsePrice:
    """가격 파싱 테스트"""

    def test_korean_format(self, service):
        """한국 가격 형식"""
        result = service._parse_price("1,234,567원")
        assert result == 1234567.0

    def test_plain_number(self, service):
        """단순 숫자"""
        result = service._parse_price("5000000")
        assert result == 5000000.0

    def test_empty_string(self, service):
        """빈 문자열"""
        result = service._parse_price("")
        assert result == 0.0

    def test_no_numbers(self, service):
        """숫자 없는 문자열"""
        result = service._parse_price("없음")
        assert result == 0.0


class TestShouldInclude:
    """필터링 판단 테스트"""

    def test_include_matching_keyword(self, service):
        """매칭 키워드 있으면 포함"""
        announcement = {
            "title": "구내식당 임대 공고",
            "content": "구내식당 운영자 모집",
        }
        assert service._should_include(announcement) is True
        assert "구내식당" in announcement["keywords_matched"]

    def test_exclude_keyword(self, service):
        """제외 키워드 있으면 제외"""
        announcement = {
            "title": "폐기물 처리 공고",
            "content": "폐기물 처리 업체 모집",
        }
        assert service._should_include(announcement) is False

    def test_no_keyword_match(self, service):
        """매칭 키워드 없으면 제외"""
        announcement = {
            "title": "일반 건설 공고",
            "content": "건설 공사 입찰",
        }
        assert service._should_include(announcement) is False

    def test_multiple_keywords_matched(self, service):
        """여러 키워드 매칭"""
        announcement = {
            "title": "카페 위탁운영 공고",
            "content": "식당 임대 운영",
        }
        assert service._should_include(announcement) is True
        assert len(announcement["keywords_matched"]) >= 2


class TestCalculateImportance:
    """중요도 계산 테스트"""

    def test_base_score(self, service):
        """기본 점수 1"""
        announcement = {
            "title": "일반 공고",
            "agency": "일반 기관",
            "keywords_matched": [],
            "estimated_price": 0,
        }
        score = service._calculate_importance(announcement)
        assert score == 1

    def test_high_value_keyword_bonus(self, service):
        """핵심 키워드 보너스"""
        announcement = {
            "title": "구내식당 위탁운영",
            "agency": "일반 기관",
            "keywords_matched": ["구내식당"],
            "estimated_price": 0,
        }
        score = service._calculate_importance(announcement)
        assert score >= 2

    def test_priority_agency_bonus(self, service):
        """우선 기관 보너스"""
        announcement = {
            "title": "식당 임대",
            "agency": "한국도로공사",
            "keywords_matched": ["식당"],
            "estimated_price": 0,
        }
        score = service._calculate_importance(announcement)
        assert score >= 2

    def test_high_price_bonus(self, service):
        """고가 보너스 (500만원 이상)"""
        announcement = {
            "title": "식당 임대",
            "agency": "일반 기관",
            "keywords_matched": ["식당"],
            "estimated_price": 10000000,
        }
        score = service._calculate_importance(announcement)
        assert score >= 2

    def test_multiple_keywords_bonus(self, service):
        """키워드 2개 이상 보너스"""
        announcement = {
            "title": "식당 카페 운영",
            "agency": "일반 기관",
            "keywords_matched": ["식당", "카페"],
            "estimated_price": 0,
        }
        score = service._calculate_importance(announcement)
        assert score >= 2

    def test_max_score_3(self, service):
        """최대 점수 3"""
        announcement = {
            "title": "구내식당 위탁운영",
            "agency": "한국도로공사",
            "keywords_matched": ["구내식당", "위탁운영", "식당"],
            "estimated_price": 100000000,
        }
        score = service._calculate_importance(announcement)
        assert score == 3


class TestParseRow:
    """테이블 행 파싱 테스트"""

    def test_insufficient_cells(self, service):
        """셀 수 부족"""
        row = MagicMock()
        row.find_all.return_value = [MagicMock()] * 3
        result = service._parse_row(row)
        assert result is None

    def test_no_title_link(self, service):
        """제목 링크 없음"""
        cells = [MagicMock() for _ in range(6)]
        cells[1].find.return_value = None
        row = MagicMock()
        row.find_all.return_value = cells
        result = service._parse_row(row)
        assert result is None

    def test_valid_row(self, service):
        """유효한 행 파싱"""
        cells = [MagicMock() for _ in range(6)]

        # 제목 링크
        title_link = MagicMock()
        title_link.get_text.return_value = "구내식당 임대"
        title_link.get.return_value = "/op/test/detail"
        cells[1].find.return_value = title_link

        # 기관명
        cells[2].get_text.return_value = "테스트 기관"
        # 입찰 기간
        cells[3].get_text.return_value = "2026-01-20 ~ 2026-01-25"
        # 추정가
        cells[4].get_text.return_value = "5,000,000원"

        row = MagicMock()
        row.find_all.return_value = cells

        result = service._parse_row(row)
        assert result is not None
        assert result["title"] == "구내식당 임대"
        assert result["agency"] == "테스트 기관"
        assert result["estimated_price"] == 5000000.0
        assert result["source"] == "Onbid"
        assert "onbid.co.kr" in result["url"]
