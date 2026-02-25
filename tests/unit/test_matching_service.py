"""
HardMatchEngine + MatchingService 단위 테스트

HardMatchEngine: 3단계 매칭 검증 (지역/면허/실적)
MatchingService: Hard + Soft + Semantic 통합 매칭
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.matching_service import HardMatchEngine, MatchingService


# ============================================
# Mock Factory Helpers
# ============================================


def make_bid(**overrides):
    """Mock BidAnnouncement 생성"""
    bid = MagicMock()
    bid.id = overrides.get("id", 1)
    bid.title = overrides.get("title", "테스트 공고")
    bid.content = overrides.get("content", "테스트 내용")
    bid.agency = overrides.get("agency", "테스트 기관")
    bid.region_code = overrides.get("region_code", None)
    bid.license_requirements = overrides.get("license_requirements", None)
    bid.min_performance = overrides.get("min_performance", None)
    bid.estimated_price = overrides.get("estimated_price", None)
    bid.importance_score = overrides.get("importance_score", 1)
    bid.url = overrides.get("url", "https://example.com")
    bid.status = overrides.get("status", "new")
    bid.keywords_matched = overrides.get("keywords_matched", [])
    bid.source = overrides.get("source", "G2B")
    return bid


def make_profile(**overrides):
    """Mock UserProfile 생성"""
    profile = MagicMock()
    profile.user_id = overrides.get("user_id", 1)
    profile.location_code = overrides.get("location_code", None)
    profile.region_code = overrides.get("region_code", None)
    profile.keywords = overrides.get("keywords", [])
    profile.company_name = overrides.get("company_name", "테스트 기업")

    # 면허 설정
    licenses = overrides.get("licenses", [])
    mock_licenses = []
    for lic in licenses:
        mock_lic = MagicMock()
        mock_lic.license_name = lic
        mock_licenses.append(mock_lic)
    profile.licenses = mock_licenses

    # 실적 설정
    performances = overrides.get("performances", [])
    mock_performances = []
    for amount in performances:
        mock_perf = MagicMock()
        mock_perf.amount = amount
        mock_performances.append(mock_perf)
    profile.performances = mock_performances

    return profile


# ============================================
# HardMatchEngine Tests
# ============================================


class TestHardMatchEngineRegion:
    """HardMatchEngine 지역 매칭 테스트"""

    def setup_method(self):
        self.engine = HardMatchEngine()

    def test_no_user_region_passes(self):
        """사용자 지역 없으면 전국 가능으로 통과"""
        bid = make_bid(region_code="11")
        profile = make_profile(location_code=None)
        match, reason = self.engine._check_region(bid, profile)
        assert match is True
        assert "전국 가능" in reason

    def test_no_bid_region_passes(self):
        """공고 지역 없으면 전국 가능으로 통과"""
        bid = make_bid(region_code=None, agency="", title="")
        profile = make_profile(location_code="11")
        match, reason = self.engine._check_region(bid, profile)
        assert match is True

    def test_region_match(self):
        """지역 일치"""
        bid = make_bid(region_code="11")
        profile = make_profile(location_code="11")
        match, reason = self.engine._check_region(bid, profile)
        assert match is True
        assert "일치" in reason

    def test_region_mismatch(self):
        """지역 불일치"""
        bid = make_bid(region_code="26")
        profile = make_profile(location_code="11")
        match, reason = self.engine._check_region(bid, profile)
        assert match is False
        assert "불일치" in reason

    def test_region_extracted_from_title(self):
        """제목에서 지역 추출"""
        bid = make_bid(region_code=None, agency="서울대학교병원", title="서울 공사")
        code = self.engine._extract_region_from_bid(bid)
        assert code == "11"

    def test_region_extracted_busan(self):
        """부산 기관명에서 추출"""
        bid = make_bid(region_code=None, agency="부산시청", title="")
        code = self.engine._extract_region_from_bid(bid)
        assert code == "26"

    def test_region_code_00_ignored(self):
        """region_code 00은 무시"""
        bid = make_bid(region_code="00", agency="", title="")
        code = self.engine._extract_region_from_bid(bid)
        assert code is None


class TestHardMatchEngineLicense:
    """HardMatchEngine 면허 매칭 테스트"""

    def setup_method(self):
        self.engine = HardMatchEngine()

    def test_no_licenses_fails(self):
        """면허 없으면 실패"""
        bid = make_bid()
        profile = make_profile(licenses=[])
        match, reason = self.engine._check_license(bid, profile)
        assert match is False
        assert "보유 면허 없음" in reason

    def test_no_license_requirement_passes(self):
        """면허 요구 없으면 통과"""
        bid = make_bid(license_requirements=None, title="일반 공고", content="내용")
        profile = make_profile(licenses=["조경공사업"])
        match, reason = self.engine._check_license(bid, profile)
        assert match is True

    def test_license_match(self):
        """면허 일치"""
        bid = make_bid(license_requirements=["조경공사업"])
        profile = make_profile(licenses=["조경공사업"])
        match, reason = self.engine._check_license(bid, profile)
        assert match is True
        assert "일치" in reason

    def test_license_partial_match(self):
        """부분 문자열 매칭"""
        bid = make_bid(license_requirements=["조경"])
        profile = make_profile(licenses=["조경공사업"])
        match, reason = self.engine._check_license(bid, profile)
        assert match is True

    def test_license_mismatch(self):
        """면허 불일치"""
        bid = make_bid(license_requirements=["전기공사업"])
        profile = make_profile(licenses=["조경공사업"])
        match, reason = self.engine._check_license(bid, profile)
        assert match is False
        assert "미보유" in reason

    def test_license_extracted_from_text(self):
        """공고 텍스트에서 면허 추출"""
        bid = make_bid(
            license_requirements=None,
            title="조경공사 입찰",
            content="조경시설 설치 공사",
        )
        result = self.engine._extract_license_requirements(bid)
        assert any("조경" in r for r in result)


class TestHardMatchEnginePerformance:
    """HardMatchEngine 실적 매칭 테스트"""

    def setup_method(self):
        self.engine = HardMatchEngine()

    def test_no_estimated_price_passes(self):
        """추정가 없으면 통과"""
        bid = make_bid(estimated_price=None)
        profile = make_profile(performances=[])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is True

    def test_zero_estimated_price_passes(self):
        """추정가 0이면 통과"""
        bid = make_bid(estimated_price=0)
        profile = make_profile(performances=[])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is True

    def test_no_performances_fails(self):
        """실적 없으면 실패"""
        bid = make_bid(estimated_price=100000000)
        profile = make_profile(performances=[])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is False
        assert "실적 없음" in reason

    def test_sufficient_performance(self):
        """실적 충분 (50% 이상)"""
        bid = make_bid(estimated_price=100000000)
        profile = make_profile(performances=[60000000])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is True
        assert "충족" in reason

    def test_insufficient_performance(self):
        """실적 부족 (50% 미만)"""
        bid = make_bid(estimated_price=100000000)
        profile = make_profile(performances=[30000000])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is False
        assert "부족" in reason

    def test_max_performance_used(self):
        """최대 실적이 사용됨"""
        bid = make_bid(estimated_price=100000000)
        profile = make_profile(performances=[10000000, 60000000, 20000000])
        match, reason = self.engine._check_performance(bid, profile)
        assert match is True

    def test_get_max_performance_empty(self):
        """실적 없으면 0 반환"""
        profile = make_profile(performances=[])
        result = self.engine._get_max_performance(profile)
        assert result == 0.0


class TestHardMatchEngineEvaluate:
    """HardMatchEngine evaluate() 통합 테스트"""

    def setup_method(self):
        self.engine = HardMatchEngine()

    def test_full_match(self):
        """모든 조건 충족"""
        bid = make_bid(
            region_code="11",
            license_requirements=["조경공사업"],
            estimated_price=100000000,
        )
        profile = make_profile(
            location_code="11",
            licenses=["조경공사업"],
            performances=[80000000],
        )
        is_match, reasons, details = self.engine.evaluate(bid, profile)
        assert is_match is True
        assert len(reasons) == 0
        assert details["region_check"]["passed"] is True
        assert details["license_check"]["passed"] is True
        assert details["performance_check"]["passed"] is True

    def test_partial_fail(self):
        """일부 조건 불충족"""
        bid = make_bid(
            region_code="26",
            license_requirements=["전기공사업"],
            estimated_price=100000000,
        )
        profile = make_profile(
            location_code="11",
            licenses=["조경공사업"],
            performances=[80000000],
        )
        is_match, reasons, details = self.engine.evaluate(bid, profile)
        assert is_match is False
        assert len(reasons) >= 1

    def test_all_fail(self):
        """모든 조건 불충족"""
        bid = make_bid(
            region_code="26",
            license_requirements=["전기공사업"],
            estimated_price=100000000,
        )
        profile = make_profile(
            location_code="11",
            licenses=["조경공사업"],
            performances=[10000000],
        )
        is_match, reasons, details = self.engine.evaluate(bid, profile)
        assert is_match is False
        assert len(reasons) == 3


class TestHardMatchEngineScore:
    """HardMatchEngine 점수 계산 테스트"""

    def setup_method(self):
        self.engine = HardMatchEngine()

    def test_full_match_score_1(self):
        """완전 매칭 → 1.0"""
        bid = make_bid(region_code=None, estimated_price=None)
        profile = make_profile(licenses=["조경공사업"])
        score = self.engine.get_matching_score(bid, profile)
        assert score == 1.0

    def test_no_match_score_partial(self):
        """부분 매칭 → 0 < score < 1"""
        bid = make_bid(
            region_code="26",
            license_requirements=None,
            estimated_price=None,
        )
        profile = make_profile(
            location_code="11",
            licenses=["조경공사업"],
        )
        score = self.engine.get_matching_score(bid, profile)
        assert 0.0 < score < 1.0


# ============================================
# MatchingService Tests
# ============================================


class TestMatchingServiceHardMatch:
    """MatchingService check_hard_match() 테스트"""

    def setup_method(self):
        with patch("app.services.matching_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = MatchingService()

    def test_no_restrictions_match(self):
        """제한 없는 공고 → 매칭"""
        bid = make_bid(region_code=None, license_requirements=None, min_performance=None)
        profile = make_profile(location_code="11", licenses=["조경공사업"])
        result = self.service.check_hard_match(profile, bid)
        assert result["is_match"] is True
        assert len(result["reasons"]) == 0

    def test_region_mismatch(self):
        """지역 불일치"""
        bid = make_bid(region_code="26")
        profile = make_profile(location_code="11")
        result = self.service.check_hard_match(profile, bid)
        assert result["is_match"] is False
        assert any("지역" in r for r in result["reasons"])

    def test_region_no_user_code(self):
        """사용자 지역 없음"""
        bid = make_bid(region_code="11")
        profile = make_profile(location_code=None)
        result = self.service.check_hard_match(profile, bid)
        assert any("지역 정보 없음" in r for r in result["reasons"])

    def test_region_code_00_ignored(self):
        """region_code 00은 전국으로 취급"""
        bid = make_bid(region_code="00")
        profile = make_profile(location_code="11")
        result = self.service.check_hard_match(profile, bid)
        assert not any("지역" in r for r in result["reasons"])

    def test_license_mismatch(self):
        """면허 불일치"""
        bid = make_bid(license_requirements=["전기공사업"])
        profile = make_profile(licenses=["조경공사업"])
        result = self.service.check_hard_match(profile, bid)
        assert result["is_match"] is False
        assert any("면허" in r for r in result["reasons"])

    def test_license_match_partial(self):
        """면허 부분 매칭"""
        bid = make_bid(license_requirements=["조경"])
        profile = make_profile(licenses=["조경공사업"])
        result = self.service.check_hard_match(profile, bid)
        assert not any("면허" in r for r in result["reasons"])

    def test_performance_insufficient(self):
        """실적 부족"""
        bid = make_bid(min_performance=100000000)
        profile = make_profile(performances=[50000000])
        result = self.service.check_hard_match(profile, bid)
        assert result["is_match"] is False
        assert any("실적" in r for r in result["reasons"])

    def test_performance_sufficient(self):
        """실적 충분"""
        bid = make_bid(min_performance=50000000)
        profile = make_profile(performances=[80000000])
        result = self.service.check_hard_match(profile, bid)
        assert not any("실적" in r for r in result["reasons"])


class TestMatchingServiceSoftMatch:
    """MatchingService calculate_soft_match() 테스트"""

    def setup_method(self):
        with patch("app.services.matching_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = MatchingService()

    def test_keyword_in_title(self):
        """제목에 키워드 매칭 → +20점"""
        bid = make_bid(title="조경공사 입찰 공고", content="")
        profile = make_profile(keywords=["조경공사"])
        result = self.service.calculate_soft_match(profile, bid)
        assert result["score"] >= 20
        assert any("제목" in b for b in result["breakdown"])

    def test_keyword_in_content(self):
        """본문에 키워드 매칭 → +5점"""
        bid = make_bid(title="일반 공고", content="조경 관련 내용입니다")
        profile = make_profile(keywords=["조경"])
        result = self.service.calculate_soft_match(profile, bid)
        assert result["score"] >= 5
        assert any("본문" in b for b in result["breakdown"])

    def test_region_match_bonus(self):
        """지역 매칭 보너스 → +10점"""
        bid = make_bid(region_code="11", title="공고", content="내용")
        profile = make_profile(location_code="11", keywords=[])
        result = self.service.calculate_soft_match(profile, bid)
        assert any("지역" in b for b in result["breakdown"])

    def test_importance_bonus(self):
        """중요도 반영"""
        bid = make_bid(importance_score=3, title="공고", content="내용")
        profile = make_profile(keywords=[])
        result = self.service.calculate_soft_match(profile, bid)
        assert any("중요도(3)" in b for b in result["breakdown"])

    def test_score_capped_at_100(self):
        """점수 최대 100"""
        bid = make_bid(
            title="조경 건축 토목 전기 통신 소방",
            content="",
            importance_score=3,
            region_code="11",
        )
        profile = make_profile(
            keywords=["조경", "건축", "토목", "전기", "통신", "소방"],
            location_code="11",
        )
        result = self.service.calculate_soft_match(profile, bid)
        assert result["score"] <= 100

    def test_no_keywords_low_score(self):
        """키워드 없으면 낮은 점수"""
        bid = make_bid(title="공고", content="내용", importance_score=1)
        profile = make_profile(keywords=[])
        result = self.service.calculate_soft_match(profile, bid)
        assert result["score"] <= 20


class TestMatchingServiceSemanticMatch:
    """MatchingService calculate_semantic_match() 테스트"""

    async def test_no_client_returns_error(self):
        """Gemini 미설정 시 에러"""
        with patch("app.services.matching_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            service = MatchingService()
        bid = make_bid(title="테스트", content="내용")
        result = await service.calculate_semantic_match("쿼리", bid)
        assert result["score"] == 0.0
        assert result["error"] is not None
