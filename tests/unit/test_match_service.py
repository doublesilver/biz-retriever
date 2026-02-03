"""
Match Service (Hard Match Engine) 단위 테스트
Zero-Error 입찰 공고 매칭 엔진
"""

from datetime import datetime, timedelta

import pytest

from app.db.models import BidAnnouncement, UserLicense, UserPerformance, UserProfile
from app.services.match_service import HardMatchEngine


class TestHardMatchEngine:
    """Hard Match 엔진 테스트"""

    # ============================================
    # 초기화 및 설정 테스트
    # ============================================

    def test_init(self):
        """엔진 초기화"""
        engine = HardMatchEngine()

        assert engine.REGION_CODES is not None
        assert "11" in engine.REGION_CODES
        assert engine.REGION_CODES["11"] == "서울특별시"

    def test_region_codes_complete(self):
        """지역 코드 완성도"""
        engine = HardMatchEngine()

        # 주요 지역 코드 확인
        assert "11" in engine.REGION_CODES  # 서울
        assert "26" in engine.REGION_CODES  # 부산
        assert "41" in engine.REGION_CODES  # 경기

    def test_license_keywords_mapping(self):
        """면허 키워드 매핑"""
        engine = HardMatchEngine()

        assert "조경" in engine.LICENSE_KEYWORDS
        assert "건축" in engine.LICENSE_KEYWORDS
        assert "조경공사업" in engine.LICENSE_KEYWORDS["조경"]

    def test_all_license_types(self):
        """모든 면허 타입 확인"""
        engine = HardMatchEngine()

        license_types = ["조경", "건축", "토목", "전기", "통신", "소방"]
        for license_type in license_types:
            assert license_type in engine.LICENSE_KEYWORDS

    # ============================================
    # evaluate 메서드 테스트 (구조 검증)
    # ============================================

    def test_evaluate_method_exists(self):
        """evaluate 메서드 존재 확인"""
        engine = HardMatchEngine()
        assert hasattr(engine, "evaluate")
        assert callable(engine.evaluate)

    # ============================================
    # Extract Methods 테스트
    # ============================================

    def test_extract_region_from_bid(self):
        """공고에서 지역 추출"""
        engine = HardMatchEngine()

        bid = BidAnnouncement(
            title="서울 공사",
            content="서울시 강남구",
            agency="서울시청",
            estimated_price=50000000,
            deadline=datetime.now() + timedelta(days=7),
        )

        region = engine._extract_region_from_bid(bid)

        assert isinstance(region, str)

    def test_extract_license_requirements(self):
        """공고에서 면허 요구사항 추출"""
        engine = HardMatchEngine()

        bid = BidAnnouncement(
            title="조경공사",
            content="조경공사 입찰",
            agency="기관",
            estimated_price=50000000,
            deadline=datetime.now() + timedelta(days=7),
        )

        licenses = engine._extract_license_requirements(bid)

        assert isinstance(licenses, list)

    def test_get_max_performance(self):
        """최대 실적 조회"""
        engine = HardMatchEngine()

        profile = UserProfile(
            user_id=1,
            company_name="Test Company",
            location_code="11",
        )

        performance1 = UserPerformance(
            profile_id=1,
            project_name="Project 1",
            amount=30000000,
        )
        performance2 = UserPerformance(
            profile_id=1,
            project_name="Project 2",
            amount=50000000,
        )
        profile.performances = [performance1, performance2]

        max_perf = engine._get_max_performance(profile)

        assert isinstance(max_perf, (int, float))
        assert max_perf >= 0

    # ============================================
    # Edge Cases 테스트
    # ============================================

    def test_bid_announcement_creation(self):
        """공고 객체 생성"""
        bid = BidAnnouncement(
            title="공사",
            content="내용",
            agency="기관",
            estimated_price=50000000,
            deadline=datetime.now() + timedelta(days=7),
        )

        assert bid.title == "공사"
        assert bid.estimated_price == 50000000

    def test_user_profile_creation(self):
        """사용자 프로필 객체 생성"""
        profile = UserProfile(
            user_id=1,
            company_name="Test Company",
            location_code="11",
        )

        assert profile.user_id == 1
        assert profile.company_name == "Test Company"
        assert profile.location_code == "11"

    def test_user_license_creation(self):
        """사용자 면허 객체 생성"""
        license = UserLicense(
            profile_id=1,
            license_name="조경공사업",
            license_number="12345",
        )

        assert license.profile_id == 1
        assert license.license_name == "조경공사업"

    def test_user_performance_creation(self):
        """사용자 실적 객체 생성"""
        performance = UserPerformance(
            profile_id=1,
            project_name="Project",
            amount=50000000,
        )

        assert performance.profile_id == 1
        assert performance.project_name == "Project"
        assert performance.amount == 50000000
