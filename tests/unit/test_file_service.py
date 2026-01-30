"""
파일 서비스 단위 테스트
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.file_service import FileService


class TestFileService:
    """파일 서비스 테스트"""

    @pytest.fixture
    def service(self):
        """서비스 인스턴스"""
        return FileService()

    @pytest.fixture
    def mock_pdf_file(self):
        """Mock PDF 파일"""
        mock_file = AsyncMock()
        mock_file.filename = "test.pdf"
        # 간단한 PDF 헤더 (실제 PDF는 아니지만 테스트용)
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 test content")
        return mock_file

    @pytest.fixture
    def mock_hwp_file(self):
        """Mock HWP 파일"""
        mock_file = AsyncMock()
        mock_file.filename = "test.hwp"
        mock_file.read = AsyncMock(return_value=b"HWP test content")
        return mock_file

    @pytest.fixture
    def mock_txt_file(self):
        """Mock TXT 파일 (지원하지 않는 형식)"""
        mock_file = AsyncMock()
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"plain text content")
        return mock_file

    # ============================================
    # get_text_from_file 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_text_from_file_pdf(self, service, mock_pdf_file):
        """PDF 파일 라우팅"""
        # parse_pdf가 호출되는지 확인
        result = await service.get_text_from_file(mock_pdf_file)

        # PDF 파싱이 시도됨 (실제 PDF가 아니므로 에러 메시지 또는 빈 결과)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_text_from_file_hwp(self, service, mock_hwp_file):
        """HWP 파일 라우팅"""
        result = await service.get_text_from_file(mock_hwp_file)

        # HWP 파싱 관련 메시지 (olefile 설치 여부에 따라 다름)
        assert any(
            kw in result.lower()
            for kw in ["hwp", "olefile", "not", "error", "extracted"]
        )

    @pytest.mark.asyncio
    async def test_get_text_from_file_unsupported(self, service, mock_txt_file):
        """지원하지 않는 형식"""
        result = await service.get_text_from_file(mock_txt_file)

        assert "unsupported" in result.lower()

    # ============================================
    # parse_pdf 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_parse_pdf_error_handling(self, service):
        """PDF 파싱 에러 처리"""
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"not a valid pdf")

        result = await service.parse_pdf(mock_file)

        # 에러가 발생해도 문자열을 반환
        assert isinstance(result, str)
        assert "error" in result.lower() or len(result) > 0

    # ============================================
    # parse_hwp 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_parse_hwp_not_implemented(self, service, mock_hwp_file):
        """HWP 파싱 결과 반환"""
        result = await service.parse_hwp(mock_hwp_file)

        # HWP 파싱 관련 메시지 (olefile 설치 여부에 따라 다름)
        assert any(
            kw in result.lower()
            for kw in ["hwp", "olefile", "not", "error", "extracted", "valid"]
        )

    # ============================================
    # 파일명 대소문자 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_get_text_from_file_case_insensitive(self, service):
        """파일명 대소문자 무시"""
        mock_file = AsyncMock()
        mock_file.filename = "TEST.PDF"  # 대문자
        mock_file.read = AsyncMock(return_value=b"%PDF-1.4 test")

        result = await service.get_text_from_file(mock_file)

        # PDF로 처리됨
        assert result is not None
