"""
ProfileService 확장 단위 테스트
- parse_business_certificate with mocked Gemini (성공, JSON in markdown, 예외)
- __init__ with Gemini 설정 분기
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.profile_service import ProfileService


def _make_service():
    """Gemini 미설정 상태의 서비스 생성"""
    with patch("app.services.profile_service.settings") as ms:
        ms.GEMINI_API_KEY = None
        return ProfileService()


class TestParseBusinessCertificate:
    """사업자등록증 AI 분석 테스트"""

    async def test_no_client_raises_valueerror(self):
        """Gemini 미설정 → ValueError"""
        service = _make_service()
        with pytest.raises(ValueError, match="Gemini"):
            await service.parse_business_certificate(b"content")

    async def test_valid_json_response(self):
        """정상 JSON 응답"""
        service = _make_service()
        mock_client = MagicMock()
        service.client = mock_client

        expected = {
            "company_name": "테스트 기업",
            "brn": "1234567890",
            "representative": "홍길동",
            "address": "서울특별시 강남구",
            "company_type": "법인사업자",
            "location_code": "11",
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(expected)

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.parse_business_certificate(b"image_bytes")

        assert result["company_name"] == "테스트 기업"
        assert result["brn"] == "1234567890"

    async def test_json_in_markdown_block(self):
        """```json 블록으로 감싸진 응답"""
        service = _make_service()
        mock_client = MagicMock()
        service.client = mock_client

        expected = {"company_name": "마크다운 기업", "brn": "9876543210"}
        raw_text = f"```json\n{json.dumps(expected)}\n```"

        mock_response = MagicMock()
        mock_response.text = raw_text

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.parse_business_certificate(b"img")

        assert result["company_name"] == "마크다운 기업"

    async def test_plain_code_block(self):
        """``` 블록으로 감싸진 응답"""
        service = _make_service()
        mock_client = MagicMock()
        service.client = mock_client

        expected = {"company_name": "코드블록 기업"}
        raw_text = f"```\n{json.dumps(expected)}\n```"

        mock_response = MagicMock()
        mock_response.text = raw_text

        with patch("asyncio.to_thread", return_value=mock_response):
            result = await service.parse_business_certificate(b"img")

        assert result["company_name"] == "코드블록 기업"

    async def test_api_exception_raises(self):
        """Gemini API 예외 → Exception 전파"""
        service = _make_service()
        mock_client = MagicMock()
        service.client = mock_client

        with patch("asyncio.to_thread", side_effect=RuntimeError("API 오류")):
            with pytest.raises(Exception, match="AI 분석 중 오류"):
                await service.parse_business_certificate(b"img")


class TestProfileServiceInit:
    """ProfileService 초기화 분기 테스트"""

    def test_no_api_key(self):
        """API 키 없음 → client=None"""
        service = _make_service()
        assert service.client is None

    def test_invalid_api_key_prefix(self):
        """API 키 prefix 불일치 → client=None"""
        with patch("app.services.profile_service.settings") as ms:
            ms.GEMINI_API_KEY = "sk-invalid-prefix"
            service = ProfileService()
        assert service.client is None

    def test_genai_import_error(self):
        """google.genai 미설치 → client=None"""
        with patch("app.services.profile_service.settings") as ms:
            ms.GEMINI_API_KEY = "AIzaFakeKeyForTesting12345"
            with patch.dict("sys.modules", {"google": None, "google.genai": None}):
                # ImportError during import google.genai
                service = ProfileService()
        assert service.client is None
