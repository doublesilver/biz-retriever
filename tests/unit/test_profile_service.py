"""
Profile Service 단위 테스트
사용자 프로필 및 면허/실적 관리
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import UserLicense, UserPerformance, UserProfile
from app.services.profile_service import ProfileService


class TestProfileService:
    """사용자 프로필 서비스 테스트"""

    # ============================================
    # get_profile 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, test_db):
        """프로필 조회 - 없음"""
        service = ProfileService()
        profile = await service.get_profile(test_db, user_id=999)

        assert profile is None

    @pytest.mark.asyncio
    async def test_get_profile_found(self, test_db):
        """프로필 조회 - 있음"""
        # 테스트 프로필 생성
        profile = UserProfile(user_id=1, company_name="Test Company", location_code="11")
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        result = await service.get_profile(test_db, user_id=1)

        assert result is not None
        assert result.company_name == "Test Company"
        assert result.location_code == "11"

    # ============================================
    # create_or_update_profile 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_create_profile(self, test_db):
        """프로필 생성"""
        service = ProfileService()
        profile_data = {
            "company_name": "New Company",
            "location_code": "26",
            "brn": "1234567890",
        }

        profile = await service.create_or_update_profile(test_db, user_id=1, profile_data=profile_data)

        assert profile.user_id == 1
        assert profile.company_name == "New Company"
        assert profile.location_code == "26"

    @pytest.mark.asyncio
    async def test_update_profile(self, test_db):
        """프로필 수정"""
        # 기존 프로필 생성
        profile = UserProfile(user_id=1, company_name="Old Company", location_code="11")
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        profile_data = {"company_name": "Updated Company", "location_code": "26"}

        updated = await service.create_or_update_profile(test_db, user_id=1, profile_data=profile_data)

        assert updated.company_name == "Updated Company"
        assert updated.location_code == "26"

    @pytest.mark.asyncio
    async def test_create_or_update_partial_update(self, test_db):
        """프로필 부분 수정"""
        profile = UserProfile(user_id=1, company_name="Original", location_code="11")
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        profile_data = {"company_name": "Modified"}

        updated = await service.create_or_update_profile(test_db, user_id=1, profile_data=profile_data)

        assert updated.company_name == "Modified"
        assert updated.location_code == "11"  # 변경되지 않음

    # ============================================
    # parse_business_certificate 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_parse_business_certificate_success(self):
        """사업자등록증 분석 성공"""
        service = ProfileService()

        # Gemini Mock
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "company_name": "Test Company",
            "brn": "1234567890",
            "representative": "John Doe",
            "address": "Seoul, Korea",
            "company_type": "법인사업자",
            "location_code": "11",
        })

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            service.client = MagicMock()

            result = await service.parse_business_certificate(b"fake_image_data")

            assert result["company_name"] == "Test Company"
            assert result["brn"] == "1234567890"
            assert result["location_code"] == "11"

    @pytest.mark.asyncio
    async def test_parse_business_certificate_no_client(self):
        """사업자등록증 분석 - 클라이언트 없음"""
        service = ProfileService()
        service.client = None

        with pytest.raises(ValueError, match="Gemini API가 구성되지 않았습니다"):
            await service.parse_business_certificate(b"fake_image_data")

    @pytest.mark.asyncio
    async def test_parse_business_certificate_markdown_format(self):
        """사업자등록증 분석 - Markdown 형식 응답"""
        service = ProfileService()

        mock_response = MagicMock()
        mock_response.text = """```json
{
    "company_name": "Test Company",
    "brn": "1234567890",
    "representative": "John Doe",
    "address": "Seoul",
    "company_type": "법인사업자",
    "location_code": "11"
}
```"""

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            service.client = MagicMock()

            result = await service.parse_business_certificate(b"fake_image_data")

            assert result["company_name"] == "Test Company"

    @pytest.mark.asyncio
    async def test_parse_business_certificate_error(self):
        """사업자등록증 분석 - 에러"""
        service = ProfileService()
        service.client = MagicMock()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="AI 분석 중 오류"):
                await service.parse_business_certificate(b"fake_image_data")

    # ============================================
    # match_location_code 테스트
    # ============================================

    def test_match_location_code_seoul(self):
        """지역 코드 매칭 - 서울"""
        service = ProfileService()
        code = service.match_location_code("서울시 강남구")
        assert code == "11"

    def test_match_location_code_busan(self):
        """지역 코드 매칭 - 부산"""
        service = ProfileService()
        code = service.match_location_code("부산광역시 해운대구")
        assert code == "26"

    def test_match_location_code_gyeonggi(self):
        """지역 코드 매칭 - 경기"""
        service = ProfileService()
        code = service.match_location_code("경기도 수원시")
        assert code == "41"

    def test_match_location_code_not_found(self):
        """지역 코드 매칭 - 없음"""
        service = ProfileService()
        code = service.match_location_code("Unknown Region")
        assert code == "99"

    # ============================================
    # get_or_create_profile 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_or_create_profile_exists(self, test_db):
        """프로필 조회 또는 생성 - 기존"""
        profile = UserProfile(user_id=1, company_name="Existing")
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        result = await service.get_or_create_profile(test_db, user_id=1)

        assert result.company_name == "Existing"

    @pytest.mark.asyncio
    async def test_get_or_create_profile_new(self, test_db):
        """프로필 조회 또는 생성 - 신규"""
        service = ProfileService()
        result = await service.get_or_create_profile(test_db, user_id=1)

        assert result.user_id == 1
        assert result.id is not None

    # ============================================
    # License Management 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_add_license(self, test_db):
        """면허 추가"""
        profile = UserProfile(user_id=1)
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        from datetime import date
        license_data = {
            "license_name": "조경공사업",
            "license_number": "12345",
            "issue_date": date(2020, 1, 1),
        }

        license = await service.add_license(test_db, profile.id, license_data)

        assert license.profile_id == profile.id
        assert license.license_name == "조경공사업"

    @pytest.mark.asyncio
    async def test_delete_license_success(self, test_db):
        """면허 삭제 성공"""
        profile = UserProfile(user_id=1)
        test_db.add(profile)
        await test_db.commit()

        license = UserLicense(
            profile_id=profile.id,
            license_name="조경공사업",
            license_number="12345",
        )
        test_db.add(license)
        await test_db.commit()

        service = ProfileService()
        result = await service.delete_license(test_db, profile.id, license.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_license_not_found(self, test_db):
        """면허 삭제 - 없음"""
        service = ProfileService()
        result = await service.delete_license(test_db, profile_id=1, license_id=999)

        assert result is False

    # ============================================
    # Performance Management 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_add_performance(self, test_db):
        """실적 추가"""
        profile = UserProfile(user_id=1)
        test_db.add(profile)
        await test_db.commit()

        service = ProfileService()
        from datetime import date
        performance_data = {
            "project_name": "Test Project",
            "amount": 10000000,
            "completion_date": date(2023, 1, 1),
        }

        performance = await service.add_performance(test_db, profile.id, performance_data)

        assert performance.profile_id == profile.id
        assert performance.project_name == "Test Project"

    @pytest.mark.asyncio
    async def test_delete_performance_success(self, test_db):
        """실적 삭제 성공"""
        profile = UserProfile(user_id=1)
        test_db.add(profile)
        await test_db.commit()

        performance = UserPerformance(
            profile_id=profile.id,
            project_name="Test Project",
            amount=10000000,
        )
        test_db.add(performance)
        await test_db.commit()

        service = ProfileService()
        result = await service.delete_performance(test_db, profile.id, performance.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_performance_not_found(self, test_db):
        """실적 삭제 - 없음"""
        service = ProfileService()
        result = await service.delete_performance(test_db, profile_id=1, performance_id=999)

        assert result is False
