import os
from typing import Any, Dict

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger


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
        if not self.client and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            self.api_key_type = "openai"
            logger.info("RAG 서비스: OpenAI API 사용 (Lightweight)")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6))
    async def analyze_bid(self, content: str) -> Dict[str, Any]:
        """
        입찰 공고 내용을 AI로 분석하여 요약 및 키워드 추출
        """
        if not self.api_key_type:
            return {"summary": "AI 분석 불가: API 키가 설정되지 않았습니다.", "keywords": []}

        prompt = f"""다음 입찰 공고를 분석하여 JSON 형식으로 응답하라.

공고 내용:
{content}

필수 추출 항목:
1. summary: 핵심 내용을 1문장으로 요약
2. keywords: 중요 키워드 3~5개 (리스트)
3. region_code: 공사/용역 현장 지역 (서울, 경기, 부산 등 광역시도 명칭. 전국이면 "전국")
4. license_requirements: 참여에 필요한 면허/자격 목록 (리스트). 없으면 빈 리스트.
5. min_performance: 실적 제한 금액 (숫자만, 없으면 0). "최근 3년 10억 이상" -> 1000000000

응답 예시:
{{
    "summary": "서울시청 구내식당 위탁운영 사업자 선정",
    "keywords": ["구내식당", "위탁운영", "급식"],
    "region_code": "서울",
    "license_requirements": ["식품접객업", "위생관리용역업"],
    "min_performance": 500000000
}}
"""

        try:
            result_json = {}

            if self.api_key_type == "gemini":
                # Gemini API (JSON Mode)
                from google.genai import types

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                import json

                result_json = json.loads(response.text)

            elif self.api_key_type == "openai":
                # OpenAI API (JSON Mode)
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an AI assistant. Respond in JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                }
                headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}

                response = await self.http_client.post(
                    "https://api.openai.com/v1/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                import json

                result_json = json.loads(data["choices"][0]["message"]["content"])

            return {
                "summary": result_json.get("summary", "분석 실패"),
                "keywords": result_json.get("keywords", []),
                "region_code": result_json.get("region_code"),
                "license_requirements": result_json.get("license_requirements", []),
                "min_performance": float(result_json.get("min_performance", 0) or 0),
            }

        except Exception as e:
            logger.error(f"AI 분석 중 오류 발생: {e}", exc_info=True)
            return {"summary": f"분석 실패: {str(e)[:50]}", "keywords": []}


rag_service = RAGService()
