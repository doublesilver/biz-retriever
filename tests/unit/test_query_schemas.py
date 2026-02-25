"""
쿼리 스키마 검증 테스트
- BidsQueryParams sanitize_keyword
- PriorityAgenciesParams validate_agencies
- KeywordParam validate_keyword
- TaskIdPath validate_task_id
"""

import pytest
from pydantic import ValidationError

from app.schemas.query import (
    BidsQueryParams,
    KeywordParam,
    PriorityAgenciesParams,
    TaskIdPath,
)


class TestBidsQueryParams:
    """BidsQueryParams 테스트"""

    def test_default_values(self):
        params = BidsQueryParams()
        assert params.skip == 0
        assert params.limit == 100
        assert params.keyword is None

    def test_sanitize_keyword(self):
        """SQL injection 문자 제거"""
        params = BidsQueryParams(keyword="구내식당'; DROP TABLE--")
        assert "'" not in params.keyword
        assert '"' not in params.keyword
        assert ";" not in params.keyword

    def test_keyword_none(self):
        """None 키워드"""
        params = BidsQueryParams(keyword=None)
        assert params.keyword is None


class TestPriorityAgenciesParams:
    """PriorityAgenciesParams 테스트"""

    def test_valid_agencies(self):
        params = PriorityAgenciesParams(agencies="서울시,경기도,부산시")
        assert params.agencies == "서울시,경기도,부산시"

    def test_too_many_agencies(self):
        """20개 초과 기관"""
        agencies = ",".join([f"기관{i}" for i in range(25)])
        with pytest.raises(ValidationError):
            PriorityAgenciesParams(agencies=agencies)

    def test_empty_agency_name(self):
        """빈 기관명"""
        with pytest.raises(ValidationError):
            PriorityAgenciesParams(agencies="서울시,,부산시")

    def test_too_long_agency_name(self):
        """100자 초과 기관명"""
        long_name = "기" * 101
        with pytest.raises(ValidationError):
            PriorityAgenciesParams(agencies=long_name)


class TestKeywordParam:
    """KeywordParam 테스트"""

    def test_valid(self):
        param = KeywordParam(keyword="구내식당")
        assert param.keyword == "구내식당"

    def test_strips_whitespace(self):
        param = KeywordParam(keyword="  식당  ")
        assert param.keyword == "식당"

    def test_blank_keyword(self):
        """공백만 있는 키워드"""
        with pytest.raises(ValidationError):
            KeywordParam(keyword="   ")


class TestTaskIdPath:
    """TaskIdPath 테스트"""

    def test_valid_task_id(self):
        path = TaskIdPath(task_id="abc-123-def")
        assert path.task_id == "abc-123-def"

    def test_invalid_characters(self):
        """특수문자 포함"""
        with pytest.raises(ValidationError):
            TaskIdPath(task_id="abc!@#$")

    def test_spaces(self):
        """공백 포함"""
        with pytest.raises(ValidationError):
            TaskIdPath(task_id="abc def")
