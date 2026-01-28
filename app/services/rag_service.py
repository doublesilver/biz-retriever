from typing import Dict, Any
import os
from app.core.config import settings
from app.core.config import settings
from app.core.logging import logger
from tenacity import retry, stop_after_attempt, wait_exponential

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=6)
    )
    async def analyze_bid(self, content: str) -> Dict[str, Any]:
        """
        입찰 공고 내용을 AI로 분석하여 요약 및 키워드 추출
        """
        if not self.api_key_type:
            return {
                "summary": "AI 분석 불가: API 키가 설정되지 않았습니다.",
                "keywords": []
            }

        prompt = f"""다음 입찰 공고를 분석하여:
1. 핵심 내용을 1문장으로 요약
2. 중요 키워드 3개 추출

공고 내용:
{content}

응답 형식:
요약: [1문장 요약]
키워드: [키워드1, 키워드2, 키워드3]
"""

        try:
            result_text = ""
            
            if self.api_key_type == "gemini":
                # Gemini API 호출 (gemini-2.5-flash 모델)
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                result_text = response.text
                
            elif self.api_key_type == "openai":
                # OpenAI API 호출 (Direct HTTP Request)
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an AI assistant for analyzing public bid announcements in Korean."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0
                }
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                response = await self.http_client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                result_text = data["choices"][0]["message"]["content"]
            
            # 간단한 파싱
            lines = result_text.strip().split('\n')
            summary = ""
            keywords = []
            
            for line in lines:
                if line.startswith("요약:"):
                    summary = line.replace("요약:", "").strip()
                elif line.startswith("키워드:"):
                    kw_text = line.replace("키워드:", "").strip()
                    keywords = [k.strip() for k in kw_text.replace('[', '').replace(']', '').split(',')]
            
            return {
                "summary": summary or result_text[:100],
                "keywords": keywords[:3] if keywords else ["AI", "분석", "완료"]
            }
            
        except Exception as e:
            logger.error(f"AI 분석 중 오류 발생: {e}", exc_info=True)
            return {
                "summary": f"분석 실패: {str(e)[:50]}",
                "keywords": []
            }

rag_service = RAGService()
