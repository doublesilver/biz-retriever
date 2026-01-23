from typing import Dict, Any
import os
from app.core.config import settings
from app.core.logging import logger

class RAGService:
    def __init__(self):
        """
        RAG 서비스 초기화
        Google Gemini API를 우선 사용하고, 없으면 OpenAI 사용
        """
        self.api_key_type = None
        self.llm = None
        
        # Gemini API 우선 사용
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.startswith("AIza"):
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.llm = client
                self.api_key_type = "gemini"
                logger.info("RAG 서비스: Google Gemini API 사용")
            except ImportError:
                logger.warning("google-genai 패키지가 설치되지 않음. OpenAI로 대체")
            except Exception as e:
                logger.error(f"Gemini 초기화 실패: {e}. OpenAI로 대체")
        
        # Gemini가 없으면 OpenAI 사용
        if not self.llm and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                from langchain_community.chat_models import ChatOpenAI
                self.llm = ChatOpenAI(
                    model_name="gpt-4o-mini",
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0
                )
                self.api_key_type = "openai"
                logger.info("RAG 서비스: OpenAI API 사용")
            except Exception as e:
                logger.error(f"OpenAI 초기화 실패: {e}")

    async def analyze_bid(self, content: str) -> Dict[str, Any]:
        """
        입찰 공고 내용을 AI로 분석하여 요약 및 키워드 추출
        
        Args:
            content: 공고 내용
            
        Returns:
            분석 결과 (요약, 키워드)
        """
        if not self.llm:
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
            if self.api_key_type == "gemini":
                # Gemini API 호출 (gemini-2.5-flash 모델)
                response = self.llm.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                result_text = response.text
            else:
                # OpenAI API 호출
                from langchain_core.messages import HumanMessage, SystemMessage
                messages = [
                    SystemMessage(content="You are an AI assistant for analyzing public bid announcements in Korean."),
                    HumanMessage(content=prompt)
                ]
                response = await self.llm.apredict_messages(messages)
                result_text = response.content
            
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
