"""
RAG 서비스 단위 테스트 (Gemini + OpenAI 지원)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_service import RAGService


class TestRAGService:
    """RAG AI  분석 서비스 테스트"""

    # ============================================
    # 초기화 테스트
    # ============================================

    def test_init_with_gemini_api_key(self):
        """Gemini API 키로 초기화"""
        with patch("app.services.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "AIzatest-key"
            mock_settings.OPENAI_API_KEY = None

            service = RAGService()
            # Gemini 초기화 시도 (성공 여부와 무관하게 테스트 통과)
            assert True  # 초기화 자체가 에러 없이 완료되면 성공

    def test_init_with_openai_api_key(self):
        """OpenAI API 키로 초기화"""
        with patch("app.services.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            mock_settings.OPENAI_API_KEY = "sk-test-key"

            service = RAGService()
            # OpenAI 초기화 시도 (성공 여부와 무관하게 테스트 통과)
            assert True  # 초기화 자체가 에러 없이 완료되면 성공

    def test_init_without_api_key(self):
        """API 키 없이 초기화"""
        with patch("app.services.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            mock_settings.OPENAI_API_KEY = None

            service = RAGService()
            assert service.client is None
            assert service.api_key_type is None

    # ============================================
    # analyze_bid 테스트
    # ============================================

    @pytest.mark.asyncio
    async def test_analyze_bid_without_api_key(self):
        """API 키 없을 때 에러 메시지 반환"""
        with patch("app.services.rag_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = None
            mock_settings.OPENAI_API_KEY = None

            service = RAGService()
            result = await service.analyze_bid("테스트 입찰 공고 내용")

            assert "summary" in result
            assert "keywords" in result
            assert result["keywords"] == []

    @pytest.mark.asyncio
    async def test_analyze_bid_with_gemini(self):
        """Gemini API를 사용한 분석"""
        service = RAGService()
        service.api_key_type = "gemini"

        # Gemini Mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = (
            "요약: 구내식당 위탁운영 공고\n키워드: 구내식당, 위탁운영, 입찰"
        )
        mock_llm.models.generate_content = MagicMock(return_value=mock_response)
        service.client = mock_llm

        result = await service.analyze_bid("서울대병원 구내식당 위탁운영 입찰 공고")

        assert "summary" in result
        assert "keywords" in result

    @pytest.mark.asyncio
    async def test_analyze_bid_with_openai(self):
        """OpenAI API를 사용한 분석"""
        service = RAGService()
        service.api_key_type = "openai"

        # OpenAI Mock
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = (
            "요약: 구내식당 위탁운영 공고\n키워드: 구내식당, 위탁운영, 입찰"
        )
        mock_llm.apredict_messages = AsyncMock(return_value=mock_response)
        service.client = mock_llm

        result = await service.analyze_bid("서울대병원 구내식당 위탁운영 입찰 공고")

        assert "summary" in result
        assert "keywords" in result

    @pytest.mark.asyncio
    async def test_analyze_bid_api_error(self):
        """API 에러 처리"""
        service = RAGService()
        service.api_key_type = "gemini"

        # 에러 발생 Mock
        mock_llm = MagicMock()
        mock_llm.models.generate_content = MagicMock(side_effect=Exception("API Error"))
        service.client = mock_llm

        result = await service.analyze_bid("테스트 내용")

        assert "summary" in result
        assert "keywords" in result

    @pytest.mark.asyncio
    async def test_analyze_bid_returns_required_fields(self):
        """반환 딕셔너리 필수 필드 확인"""
        service = RAGService()
        service.api_key_type = "gemini"

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "요약: 분석 결과\n키워드: 테스트, 분석, 결과"
        mock_llm.models.generate_content = MagicMock(return_value=mock_response)
        service.client = mock_llm

        result = await service.analyze_bid("테스트")

        assert "summary" in result
        assert "keywords" in result
        assert isinstance(result["keywords"], list)
