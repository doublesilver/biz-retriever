"""
G2BCrawlerService 확장 단위 테스트
- _parse_api_response
- _parse_datetime
- _should_notify
- calculate_importance_score
"""

import pytest

from app.services.crawler_service import G2BCrawlerService


@pytest.fixture
def service():
    return G2BCrawlerService()


class TestParseApiResponse:
    """API 응답 파싱 테스트"""

    def test_empty_items(self, service):
        """빈 아이템"""
        data = {"response": {"body": {"items": []}}}
        result = service._parse_api_response(data)
        assert result == []

    def test_valid_items(self, service):
        """유효한 아이템"""
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "테스트 공고",
                            "bidNtceDtl": "상세 내용",
                            "ntceInsttNm": "테스트 기관",
                            "bidNtceDt": "202601201000",
                            "bidClseDt": "202601271800",
                            "bidNtceUrl": "https://example.com",
                            "presmptPrce": "100000000",
                        }
                    ]
                }
            }
        }
        result = service._parse_api_response(data)
        assert len(result) == 1
        assert result[0]["title"] == "테스트 공고"
        assert result[0]["agency"] == "테스트 기관"
        assert result[0]["estimated_price"] == 100000000.0
        assert result[0]["source"] == "G2B"

    def test_missing_posted_at(self, service):
        """게시일 없는 경우 현재 시간 사용"""
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "공고",
                            "bidNtceDtl": "",
                            "ntceInsttNm": "기관",
                            "bidNtceDt": None,
                            "bidClseDt": None,
                            "bidNtceUrl": "",
                            "presmptPrce": "0",
                        }
                    ]
                }
            }
        }
        result = service._parse_api_response(data)
        assert len(result) == 1
        assert result[0]["posted_at"] is not None

    def test_missing_body(self, service):
        """body 없는 경우"""
        data = {"response": {}}
        result = service._parse_api_response(data)
        assert result == []

    def test_empty_content_fallback(self, service):
        """내용 없는 경우 기본값"""
        data = {
            "response": {
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "공고",
                            "bidNtceDtl": "",
                            "ntceInsttNm": "",
                            "bidNtceDt": "202601201000",
                            "bidClseDt": None,
                            "bidNtceUrl": "",
                            "presmptPrce": None,
                        }
                    ]
                }
            }
        }
        result = service._parse_api_response(data)
        assert result[0]["content"] == "내용 없음"


class TestParseDatetime:
    """날짜 파싱 테스트"""

    def test_valid_datetime(self, service):
        """유효한 날짜"""
        result = service._parse_datetime("202601201000")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 20
        assert result.hour == 10

    def test_none_input(self, service):
        """None 입력"""
        result = service._parse_datetime(None)
        assert result is None

    def test_empty_string(self, service):
        """빈 문자열"""
        result = service._parse_datetime("")
        assert result is None

    def test_invalid_format(self, service):
        """잘못된 형식"""
        result = service._parse_datetime("2026-01-20")
        assert result is None


class TestShouldNotify:
    """필터링 판단 테스트"""

    def test_include_keyword_match(self, service):
        """포함 키워드 매칭"""
        announcement = {
            "title": "구내식당 위탁운영",
            "content": "식당 운영 공고",
        }
        result = service._should_notify(announcement)
        assert result is True
        assert len(announcement["keywords_matched"]) >= 1

    def test_exclude_keyword_reject(self, service):
        """제외 키워드 매칭 시 거절"""
        announcement = {
            "title": "폐기물 처리 공고",
            "content": "폐기물 관련",
        }
        result = service._should_notify(announcement)
        assert result is False

    def test_no_keyword_match(self, service):
        """매칭 키워드 없으면 거절"""
        announcement = {
            "title": "일반 건설 공사",
            "content": "건설 관련",
        }
        result = service._should_notify(announcement)
        assert result is False

    def test_custom_keywords(self, service):
        """사용자 정의 키워드"""
        announcement = {
            "title": "특별 공고",
            "content": "맞춤 키워드 포함",
        }
        result = service._should_notify(
            announcement,
            exclude_keywords=[],
            include_keywords=["맞춤 키워드"],
        )
        assert result is True

    def test_exclude_overrides_include(self, service):
        """제외 키워드가 포함 키워드보다 우선"""
        announcement = {
            "title": "구내식당 폐기물 처리",
            "content": "",
        }
        result = service._should_notify(announcement)
        assert result is False


class TestCalculateImportanceScore:
    """중요도 점수 계산 테스트"""

    def test_base_score(self, service):
        """기본 점수 1"""
        announcement = {
            "title": "일반 공고",
            "keywords_matched": [],
            "estimated_price": 0,
        }
        score = service.calculate_importance_score(announcement)
        assert score == 1

    def test_high_value_keyword(self, service):
        """핵심 키워드 보너스"""
        announcement = {
            "title": "구내식당 위탁운영",
            "keywords_matched": [],
            "estimated_price": 0,
        }
        score = service.calculate_importance_score(announcement)
        assert score >= 2

    def test_high_price(self, service):
        """1억 이상 금액 보너스"""
        announcement = {
            "title": "일반 공고",
            "keywords_matched": [],
            "estimated_price": 200000000,
        }
        score = service.calculate_importance_score(announcement)
        assert score >= 2

    def test_many_keywords(self, service):
        """키워드 3개 이상 보너스"""
        announcement = {
            "title": "일반 공고",
            "keywords_matched": ["kw1", "kw2", "kw3"],
            "estimated_price": 0,
        }
        score = service.calculate_importance_score(announcement)
        assert score >= 2

    def test_max_score(self, service):
        """최대 점수 3"""
        announcement = {
            "title": "구내식당 위탁운영",
            "keywords_matched": ["구내식당", "위탁운영", "식당운영"],
            "estimated_price": 500000000,
        }
        score = service.calculate_importance_score(announcement)
        assert score == 3
