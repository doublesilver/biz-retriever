"""
ProfileService 단위 테스트
- 프로필 CRUD
- 면허/실적 관리
- 지역 코드 매칭
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.profile_service import ProfileService


class TestMatchLocationCode:
    """주소 기반 지역 코드 매칭 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    def test_seoul(self):
        assert self.service.match_location_code("서울특별시 강남구") == "11"

    def test_busan(self):
        assert self.service.match_location_code("부산광역시 해운대구") == "26"

    def test_daegu(self):
        assert self.service.match_location_code("대구광역시 중구") == "27"

    def test_incheon(self):
        assert self.service.match_location_code("인천광역시 남동구") == "28"

    def test_gwangju(self):
        assert self.service.match_location_code("광주광역시 서구") == "29"

    def test_daejeon(self):
        assert self.service.match_location_code("대전광역시 유성구") == "30"

    def test_ulsan(self):
        assert self.service.match_location_code("울산광역시 중구") == "31"

    def test_sejong(self):
        assert self.service.match_location_code("세종특별자치시") == "36"

    def test_gyeonggi(self):
        assert self.service.match_location_code("경기도 수원시") == "41"

    def test_gangwon(self):
        assert self.service.match_location_code("강원도 춘천시") == "42"

    def test_chungbuk(self):
        assert self.service.match_location_code("충북 청주시") == "43"

    def test_chungnam(self):
        assert self.service.match_location_code("충남 천안시") == "44"

    def test_jeonbuk(self):
        assert self.service.match_location_code("전북 전주시") == "45"

    def test_jeonnam(self):
        assert self.service.match_location_code("전남 목포시") == "46"

    def test_gyeongbuk(self):
        assert self.service.match_location_code("경북 포항시") == "47"

    def test_gyeongnam(self):
        assert self.service.match_location_code("경남 창원시") == "48"

    def test_jeju(self):
        assert self.service.match_location_code("제주특별자치도") == "49"

    def test_unknown_returns_99(self):
        assert self.service.match_location_code("알 수 없는 지역") == "99"


class TestGetProfile:
    """프로필 조회 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_get_existing_profile(self):
        mock_profile = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_profile

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.get_profile(session, 1)
        assert result == mock_profile

    async def test_get_nonexistent_profile(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.get_profile(session, 999)
        assert result is None


class TestCreateOrUpdateProfile:
    """프로필 생성/수정 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_update_existing_profile(self):
        mock_profile = MagicMock()
        mock_profile.company_name = "기존 기업"
        self.service.get_profile = AsyncMock(return_value=mock_profile)

        session = AsyncMock()
        result = await self.service.create_or_update_profile(session, 1, {"company_name": "새 기업"})
        assert result.company_name == "새 기업"
        session.commit.assert_called_once()

    async def test_create_new_profile(self):
        self.service.get_profile = AsyncMock(return_value=None)

        session = AsyncMock()
        result = await self.service.create_or_update_profile(session, 1, {"company_name": "새 기업"})
        session.add.assert_called_once()
        session.commit.assert_called_once()


class TestGetOrCreateProfile:
    """프로필 조회 또는 생성 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_get_existing(self):
        mock_profile = MagicMock()
        self.service.get_profile = AsyncMock(return_value=mock_profile)

        session = AsyncMock()
        result = await self.service.get_or_create_profile(session, 1)
        assert result == mock_profile
        session.add.assert_not_called()

    async def test_create_new(self):
        self.service.get_profile = AsyncMock(return_value=None)

        session = AsyncMock()
        result = await self.service.get_or_create_profile(session, 1)
        session.add.assert_called_once()
        session.commit.assert_called_once()


class TestAddLicense:
    """면허 추가 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_add_license(self):
        session = AsyncMock()
        result = await self.service.add_license(
            session, 1, {"license_name": "조경공사업", "license_number": "제2024-001호"}
        )
        session.add.assert_called_once()
        session.commit.assert_called_once()


class TestDeleteLicense:
    """면허 삭제 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_delete_existing(self):
        mock_license = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_license

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_license(session, 1, 1)
        assert result is True
        session.delete.assert_called_once_with(mock_license)

    async def test_delete_nonexistent(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_license(session, 1, 999)
        assert result is False


class TestAddPerformance:
    """실적 추가 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_add_performance(self):
        session = AsyncMock()
        result = await self.service.add_performance(session, 1, {"project_name": "테스트 공사", "amount": 1000000000})
        session.add.assert_called_once()
        session.commit.assert_called_once()


class TestDeletePerformance:
    """실적 삭제 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_delete_existing(self):
        mock_perf = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_perf

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_performance(session, 1, 1)
        assert result is True

    async def test_delete_nonexistent(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = mock_result

        result = await self.service.delete_performance(session, 1, 999)
        assert result is False


class TestParseBusinessCertificate:
    """사업자등록증 파싱 테스트"""

    def setup_method(self):
        with patch("app.services.profile_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            self.service = ProfileService()

    async def test_no_client_raises(self):
        """Gemini 미설정 시 에러"""
        with pytest.raises(ValueError, match="Gemini"):
            await self.service.parse_business_certificate(b"fake_content")
