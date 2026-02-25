import asyncio
import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.core.config import settings
from app.core.logging import logger
from app.db.models import BidAnnouncement


class ConstraintService:
    """
    제약 조건 추출 서비스 (Phase 3 Hard Match)
    Gemini AI를 사용하여 입찰 공고 텍스트/첨부파일에서 핵심 제약 조건(지역, 면허, 실적)을 추출
    """

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY Missing in ConstraintService")

    async def extract_constraints(self, bid: BidAnnouncement) -> Dict[str, Any]:
        """
        공고에서 제약 조건 추출
        """
        if not self.model:
            return {}

        # 1. 대상 텍스트 수집 (제목 + 본문 + 첨부파일 내용)
        full_text = f"제목: {bid.title}\n발주처: {bid.agency}\n본문: {bid.content}\n"
        if bid.attachment_content:
            full_text += f"\n첨부파일 내용 (일부): {bid.attachment_content[:10000]}"  # 10k chars limit

        # 2. Gemini 호출
        prompt = """
        당신은 입찰 공고 분석 전문가입니다. 다음 공고 텍스트에서 '입찰 참가 자격'과 관련된 핵심 제약 조건을 JSON으로 추출하세요.
        
        [추출 항목]
        1. region_code: 공사 현장 또는 납품 장소가 특정 지역으로 제한된 경우, 해당 지역의 코드를 2자리 문자열로 출력 (없으면 "00").
           - 코드표: 서울(11), 부산(26), 대구(27), 인천(28), 광주(29), 대전(30), 울산(31), 세종(36), 경기(41), 강원(42), 충북(43), 충남(44), 전북(45), 전남(46), 경북(47), 경남(48), 제주(49)
           - 예: "경기도 용인시" -> "41", "서울" -> "11", "전국" -> "00"
        
        2. license_requirements: 입찰 참가에 필요한 면허/자격증 명칭 리스트 (JSON Array).
           - 예: ["정보통신공사업", "소프트웨어사업자"]
           - 없으면 빈 리스트 []
        
        3. min_performance: 실적 제한이 있는 경우, 최소 요구 실적 금액(원 단위, 숫자, Float).
           - 단위 변환 필수: "1억원" -> 100000000.0, "5천만원" -> 50000000.0, "10억" -> 1000000000.0
           - 금액 제한이 없으면 0.0
        
        [출력 예시]
        {
            "region_code": "11",
            "license_requirements": ["정보통신공사업"],
            "min_performance": 100000000.0
        }
        
        [공고 텍스트]
        """

        try:
            response = await asyncio.to_thread(
                self.model.generate_content, f"{prompt}\n{full_text}"
            )

            # 3. 파싱
            text_resp = response.text
            if "```json" in text_resp:
                text_resp = text_resp.split("```json")[1].split("```")[0]
            elif "```" in text_resp:
                text_resp = text_resp.split("```")[1].split("```")[0]

            data = json.loads(text_resp.strip())

            # Validation
            data["region_code"] = str(data.get("region_code", "00"))
            data["license_requirements"] = list(data.get("license_requirements", []))
            data["min_performance"] = float(data.get("min_performance", 0.0))

            return data

        except Exception as e:
            logger.error(f"Constraint extraction failed for Bid {bid.id}: {e}")
            return {}


constraint_service = ConstraintService()
