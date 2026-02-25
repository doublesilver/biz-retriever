"""
RAGService 확장 테스트
- analyze_bid: no API key, gemini, openai, exception
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rag_service import RAGService


class TestAnalyzeBid:
    """analyze_bid 테스트"""

    async def test_no_api_key(self):
        """API 키 없으면 기본 응답"""
        svc = RAGService.__new__(RAGService)
        svc.api_key_type = None
        svc.client = None

        result = await svc.analyze_bid("테스트 공고 내용")
        assert "AI 분석 불가" in result["summary"]
        assert result["keywords"] == []

    async def test_gemini_success(self):
        """Gemini API 성공"""
        svc = RAGService.__new__(RAGService)
        svc.api_key_type = "gemini"
        svc.client = MagicMock()

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "summary": "구내식당 위탁운영 공고",
            "keywords": ["구내식당", "위탁운영"],
            "region_code": "서울",
            "license_requirements": [],
            "min_performance": 0.0,
        }

        mock_instructor = MagicMock()
        mock_instructor.chat.completions.create.return_value = mock_result

        # Mock the 'from google import genai' inside the function body
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            with patch("app.services.rag_service.instructor") as mock_inst:
                mock_inst.from_gemini.return_value = mock_instructor
                mock_inst.Mode.GEMINI_JSON = "gemini_json"
                result = await svc.analyze_bid("테스트 공고")

        assert result["summary"] == "구내식당 위탁운영 공고"

    async def test_openai_success(self):
        """OpenAI API 성공"""
        svc = RAGService.__new__(RAGService)
        svc.api_key_type = "openai"
        svc.client = None

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "summary": "건설 공사 공고",
            "keywords": ["건설"],
            "region_code": None,
            "license_requirements": ["건설업"],
            "min_performance": 50000000,
        }

        mock_instructor = MagicMock()
        mock_instructor.chat.completions.create = AsyncMock(return_value=mock_result)

        mock_openai_client = MagicMock()

        with patch("openai.AsyncOpenAI", return_value=mock_openai_client):
            with patch("app.services.rag_service.instructor") as mock_inst:
                mock_inst.from_openai.return_value = mock_instructor
                result = await svc.analyze_bid("건설 공사 공고")

        assert result["summary"] == "건설 공사 공고"

    async def test_exception_returns_error(self):
        """예외 발생 시 에러 응답"""
        svc = RAGService.__new__(RAGService)
        svc.api_key_type = "gemini"
        svc.client = MagicMock()

        mock_genai = MagicMock()
        mock_genai.Client.side_effect = Exception("API error")
        mock_google = MagicMock()
        mock_google.genai = mock_genai

        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            result = await svc.analyze_bid("테스트")

        assert "분석 실패" in result["summary"]
