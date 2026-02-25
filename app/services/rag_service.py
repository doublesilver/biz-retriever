import os
from typing import Any, Dict

import instructor
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger

# ============================================
# Pydantic Models for Type-Safe AI Output
# ============================================


class BidAnalysisResult(BaseModel):
    """
    입찰 공고 AI 분석 결과 (타입 안전)

    Instructor를 통해 LLM 출력이 자동으로 이 스키마에 맞게 검증됩니다.
    JSON 파싱 오류, 필드 누락, 타입 불일치 등이 자동으로 방지됩니다.
    """

    summary: str = Field(..., description="공고 핵심 내용을 1문장으로 요약")
    keywords: list[str] = Field(default_factory=list, description="중요 키워드 3-5개")
    region_code: str | None = Field(
        None, description="공사/용역 현장 지역 (광역시도명 또는 '전국')"
    )
    license_requirements: list[str] = Field(
        default_factory=list, description="필요한 면허/자격 목록"
    )
    min_performance: float = Field(
        default=0.0, description="실적 제한 금액 (숫자, 없으면 0)"
    )


class RAGService:
    def __init__(self):
        """
        RAG 서비스 초기화
        Google Gemini API를 우선 사용하고, 없으면 OpenAI 사용
        """
        self.api_key_type = None
        self.client = None

        # httpx client for OpenAI fallback
        import httpx

        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Gemini API 우선 사용
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.startswith("AIza"):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.client = client
                self.api_key_type = "gemini"
                logger.info("RAG 서비스: Google Gemini API 사용")
            except ImportError:
                logger.warning("google-genai 패키지가 설치되지 않음. OpenAI로 대체")
            except Exception as e:
                logger.error(f"Gemini 초기화 실패: {e}. OpenAI로 대체")

        # Gemini가 없으면 OpenAI 확인
        if (
            not self.client
            and settings.OPENAI_API_KEY
            and settings.OPENAI_API_KEY.startswith("sk-")
        ):
            self.api_key_type = "openai"
            logger.info("RAG 서비스: OpenAI API 사용 (Lightweight)")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6)
    )
    async def analyze_bid(self, content: str) -> Dict[str, Any]:
        """
        입찰 공고 내용을 AI로 분석하여 요약 및 키워드 추출

        Instructor를 사용하여 타입 안전한 출력 보장:
        - JSON 파싱 오류 자동 방지
        - Pydantic 검증 통과 보장
        - 필드 누락/타입 불일치 자동 재시도
        """
        if not self.api_key_type:
            return {
                "summary": "AI 분석 불가: API 키가 설정되지 않았습니다.",
                "keywords": [],
                "region_code": None,
                "license_requirements": [],
                "min_performance": 0.0,
            }

        prompt = f"""다음 입찰 공고를 분석하세요:

{content}

필수 추출 항목:
1. summary: 핵심 내용을 1문장으로 요약
2. keywords: 중요 키워드 3-5개
3. region_code: 공사/용역 현장 지역 (광역시도명 또는 '전국')
4. license_requirements: 필요한 면허/자격 목록
5. min_performance: 실적 제한 금액 (숫자, 없으면 0)
"""

        try:
            if self.api_key_type == "gemini":
                # Instructor + Gemini (Type-Safe)
                from google import genai

                gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

                # Instructor로 Gemini 클라이언트 래핑
                instructor_client = instructor.from_gemini(
                    client=gemini_client, mode=instructor.Mode.GEMINI_JSON
                )

                # Pydantic 모델로 자동 검증된 응답 받기
                result: BidAnalysisResult = instructor_client.chat.completions.create(
                    model="gemini-2.0-flash-exp",
                    response_model=BidAnalysisResult,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Pydantic 모델을 dict로 변환
                return result.model_dump()

            elif self.api_key_type == "openai":
                # Instructor + OpenAI (Type-Safe)
                from openai import AsyncOpenAI

                openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

                # Instructor로 OpenAI 클라이언트 래핑
                instructor_client = instructor.from_openai(openai_client)

                # Pydantic 모델로 자동 검증된 응답 받기
                result: BidAnalysisResult = (
                    await instructor_client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_model=BidAnalysisResult,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                    )
                )

                return result.model_dump()

        except Exception as e:
            logger.error(f"AI 분석 중 오류 발생: {e}", exc_info=True)
            return {
                "summary": f"분석 실패: {str(e)[:50]}",
                "keywords": [],
                "region_code": None,
                "license_requirements": [],
                "min_performance": 0.0,
            }


rag_service = RAGService()
