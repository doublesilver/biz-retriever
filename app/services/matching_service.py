from typing import List, Dict, Any, Optional
from app.db.models import BidAnnouncement, UserProfile, UserLicense, UserPerformance
from app.core.config import settings
from app.core.logging import logger
import asyncio
import json

class MatchingService:
    """
    매칭 엔진 (Hard Match)
    사용자 프로필과 입찰 공고의 제약 조건을 비교하여 입찰 가능 여부를 판단
    """

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("MatchingService: Gemini 2.5 Flash client initialized for Semantic Search")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini in MatchingService: {e}")

    def check_hard_match(self, user_profile: UserProfile, bid: BidAnnouncement) -> Dict[str, Any]:
        """
        Hard Match 실행
        
        Returns:
            {
                "is_match": bool,
                "reasons": List[str]  # 불일치 사유 (매칭 실패 시)
            }
        """
        reasons = []
        
        # 1. 지역 제한 확인 (Region Code)
        # bid.region_code가 "00"이면 전국, None이면 제한 없음으로 간주
        if bid.region_code and bid.region_code != "00":
            # 사용자 지역 코드와 비교
            if not user_profile.location_code:
                reasons.append(f"사용자 지역 정보 없음 (공고 제한: {bid.region_code})")
            elif user_profile.location_code != bid.region_code:
                reasons.append(f"지역 불일치 (공고: {bid.region_code}, 사용자: {user_profile.location_code})")

        # 2. 면허 제한 확인 (License Requirements)
        if bid.license_requirements:
            # 사용자가 보유한 면허 이름 집합
            user_licenses = {l.license_name for l in user_profile.licenses}
            
            # 공고 요구 면허 중 하나라도 보유하면 통과 (OR 조건 가정 - MVP)
            # 만약 AND 조건이라면 로직 수정 필요
            # MVP: "입찰 참가 자격"에 나열된 것 중 하나만 있어도 되는 경우가 많음 (공동도급 제외)
            # 하지만 안전하게 가려면? -> 일단 OR로 구현하고 로그 남김
            
            # 요구 면허 리스트 중 보유한 것이 하나도 없으면 실패
            # bid.license_requirements is a list of strings
            has_valid_license = False
            for req_license in bid.license_requirements:
                if any(req_license in ul for ul in user_licenses): 
                    # 부분 일치 허용 (예: "정보통신공사업" vs "정보통신공사업 면허")
                    has_valid_license = True
                    break
            
            if not has_valid_license:
                reasons.append(f"필요 면허 미보유 (요구: {', '.join(bid.license_requirements)})")

        # 3. 실적 제한 확인 (Minimum Performance)
        if bid.min_performance and bid.min_performance > 0:
            # 사용자의 최대 단일 실적 금액 확인 (또는 총액? 공고마다 다름)
            # MVP: 사용자의 '가장 큰 실적'이 요구조건보다 커야 함
            max_user_perf = 0.0
            if user_profile.performances:
                max_user_perf = max([p.amount for p in user_profile.performances])
            
            if max_user_perf < bid.min_performance:
                reasons.append(f"실적 기준 미달 (요구: {bid.min_performance:,}원, 보유최대: {max_user_perf:,}원)")

        return {
            "is_match": len(reasons) == 0,
            "reasons": reasons
        }

    def calculate_soft_match(self, user_profile: UserProfile, bid: BidAnnouncement) -> Dict[str, Any]:
        """
        Soft Match 실행 (정성적 평가)
        
        Returns:
            {
                "score": int, # 0~100
                "breakdown": List[str] # 점수 산출 근거
            }
        """
        score = 0
        breakdown = []
        
        # 관심 키워드 (기본값: 빈 리스트)
        user_keywords = user_profile.keywords or []
        
        # 1. 키워드 매칭 (제목: 20점/개, 내용: 5점/개)
        # Cap: 키워드로 최대 60점 채우기
        keyword_score = 0
        matched_in_title = []
        matched_in_content = []
        
        bid_title = bid.title.lower() if bid.title else ""
        bid_content = bid.content.lower() if bid.content else ""
        
        for k in user_keywords:
            k_lower = k.lower()
            if k_lower in bid_title:
                keyword_score += 20
                matched_in_title.append(k)
            elif k_lower in bid_content:
                keyword_score += 5
                matched_in_content.append(k)
        
        if matched_in_title:
            breakdown.append(f"제목 키워드 포함 (+{len(matched_in_title)*20}): {', '.join(matched_in_title)}")
        if matched_in_content:
            breakdown.append(f"본문 키워드 포함 (+{len(matched_in_content)*5}): {', '.join(matched_in_content)}")
            
        score += keyword_score
        
        # 2. 지역 매칭 (+10점)
        # 이미 Hard Match에서 걸러졌지만, 선호 지역일 경우 가산점
        if user_profile.location_code and bid.region_code:
            if user_profile.location_code == bid.region_code:
                score += 10
                breakdown.append(f"선호 지역 일치 (+10): {bid.region_code}")
                
        # 3. 중요도 점수 반영 (1~3점 -> 5, 10, 15점)
        importance_bonus = (bid.importance_score or 1) * 5
        score += importance_bonus
        breakdown.append(f"공고 중요도({bid.importance_score}) 반영 (+{importance_bonus})")
        
        # 점수 보정 (0 ~ 100)
        final_score = min(max(score, 0), 100)
        
        return {
            "score": final_score,
            "breakdown": breakdown
        }

    async def calculate_semantic_match(self, user_query: str, bid: BidAnnouncement) -> Dict[str, Any]:
        """
        Gemini 2.5 Flash를 사용하여 사용자의 자연어 쿼리와 입찰 공고 간의 의미적 유사도를 계산합니다.
        
        Returns:
            Dict[str, Any]: {"score": float (0.0~1.0), "reasoning": str, "error": str}
        """
        if not self.client:
            return {"score": 0.0, "error": "Gemini Client not initialized"}

        prompt = f"""
        You are an expert procurement analyst. Evalute the relevance between the User Query and the Bid Announcement.
        
        User Query: "{user_query}"
        
        Bid Announcement:
        Title: "{bid.title}"
        Content: "{bid.content[:1000]}"  # Truncate content specifically to save tokens

        Task:
        1. Analyze the intent of the User Query.
        2. Determine if the Bid Announcement satisfies the query (Semantic Match).
        3. Assign a relevance score between 0.0 and 1.0.
           - 1.0: Perfect match (e.g., specific location and category match exactly).
           - 0.8~0.9: High relevance (Same category, broader location matches - e.g. Jeju City is inside Jeju Island).
           - 0.5~0.7: Partial relevance (Same industry but different specific task, or location ambiguous).
           - 0.1~0.4: Low relevance (Keywords present but context different).
           - 0.0: Irrelevant.
           
        *IMPORTANT*: Be generous with location matching. if the query is a province (e.g., Jeju-do) and the bid is a city within it (e.g., Jeju-si), consider it a High Relevance match (0.8+).

        Output Format:
        Provide the response in pure JSON format WITHOUT Markdown blocks.
        {{
            "reasoning": "Explain why you assigned this score in Korean.",
            "score": 0.0
        }}
        """

        try:
            # Run blocking Gemini call in thread pool
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            # Raw response processing
            raw_text = response.text.strip()
            # Clean markdown code blocks if present
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "", 1).replace("```", "", 1).strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1).strip()

            import json
            try:
                data = json.loads(raw_text)
                score = float(data.get("score", 0.0))
                reasoning = data.get("reasoning", "No reasoning provided.")
                
                # logger.info(f"Gemini Match: {user_query} vs {bid.title} -> {score} ({reasoning})")
                return {"score": score, "reasoning": reasoning, "error": None}
            except json.JSONDecodeError:
                logger.error(f"Gemini JSON Parse Error. Raw: {raw_text}")
                return {"score": 0.0, "reasoning": f"JSON Parse Error: {raw_text[:50]}...", "error": "JSON Parse Error"}

        except Exception as e:
            logger.error(f"Gemini Semantic Match Error: {e}")
            return {"score": 0.0, "error": str(e)}

matching_service = MatchingService()
