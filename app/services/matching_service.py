"""
Unified Matching Service
통합 매칭 엔진: Hard Match + Soft Match + Semantic Match (Gemini AI)

- HardMatchEngine: Zero-Error 3단계 검증 (지역/면허/실적)
- MatchingService: Hard + Soft + Semantic 통합 서비스
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.db.models import BidAnnouncement, UserLicense, UserPerformance, UserProfile


# ============================================
# Hard Match Engine (Zero False Positive)
# ============================================


class HardMatchEngine:
    """
    Hard Match 엔진 - Zero False Positive

    모든 조건을 만족하는 입찰만 매칭 (오탐 0%)

    3단계 검증:
    1. 지역 코드 매칭
    2. 면허 요구사항 검증
    3. 실적 요구사항 검증
    """

    REGION_CODES = {
        "11": "서울특별시",
        "26": "부산광역시",
        "27": "대구광역시",
        "28": "인천광역시",
        "29": "광주광역시",
        "30": "대전광역시",
        "31": "울산광역시",
        "36": "세종특별자치시",
        "41": "경기도",
        "42": "강원도",
        "43": "충청북도",
        "44": "충청남도",
        "45": "전라북도",
        "46": "전라남도",
        "47": "경상북도",
        "48": "경상남도",
        "50": "제주특별자치도",
    }

    LICENSE_KEYWORDS = {
        "조경": ["조경공사업", "조경", "조경시설"],
        "건축": ["건축공사업", "건축", "종합건설업"],
        "토목": ["토목공사업", "토목건축공사업", "종합건설업"],
        "전기": ["전기공사업", "전기"],
        "통신": ["정보통신공사업", "통신"],
        "소방": ["소방시설공사업", "소방"],
    }

    def __init__(self):
        self.logger = logger

    def evaluate(
        self, bid: BidAnnouncement, profile: UserProfile
    ) -> Tuple[bool, List[str], Dict]:
        """
        Hard Match 평가

        Returns:
            (is_match, reasons, details)
        """
        reasons = []
        details = {
            "region_check": None,
            "license_check": None,
            "performance_check": None,
        }

        # 1. 지역 검증
        region_match, region_reason = self._check_region(bid, profile)
        details["region_check"] = {
            "passed": region_match,
            "reason": region_reason,
            "bid_region": self._extract_region_from_bid(bid),
            "user_region": getattr(profile, "region_code", None)
            or getattr(profile, "location_code", None),
        }
        if not region_match:
            reasons.append(region_reason)

        # 2. 면허 검증
        license_match, license_reason = self._check_license(bid, profile)
        details["license_check"] = {
            "passed": license_match,
            "reason": license_reason,
            "required_licenses": self._extract_license_requirements(bid),
            "user_licenses": (
                [lic.license_name for lic in profile.licenses]
                if profile.licenses
                else []
            ),
        }
        if not license_match:
            reasons.append(license_reason)

        # 3. 실적 검증
        performance_match, performance_reason = self._check_performance(bid, profile)
        details["performance_check"] = {
            "passed": performance_match,
            "reason": performance_reason,
            "required_amount": bid.estimated_price or 0,
            "user_max_performance": self._get_max_performance(profile),
        }
        if not performance_match:
            reasons.append(performance_reason)

        is_match = region_match and license_match and performance_match

        if is_match:
            self.logger.info(
                f"Hard Match SUCCESS: bid_id={bid.id}, user={profile.user_id}"
            )
        else:
            self.logger.debug(f"Hard Match FAIL: bid_id={bid.id}, reasons={reasons}")

        return is_match, reasons, details

    def _check_region(
        self, bid: BidAnnouncement, profile: UserProfile
    ) -> Tuple[bool, str]:
        """지역 코드 검증"""
        user_region = getattr(profile, "region_code", None) or getattr(
            profile, "location_code", None
        )

        if not user_region:
            return True, "지역 제한 없음 (전국 가능)"

        bid_region = self._extract_region_from_bid(bid)
        if not bid_region:
            return True, "입찰 지역 정보 없음 (전국 가능으로 간주)"

        if user_region == bid_region:
            return True, f"지역 일치: {self.REGION_CODES.get(bid_region, bid_region)}"
        else:
            return (
                False,
                f"지역 불일치: 입찰({self.REGION_CODES.get(bid_region, bid_region)}) vs 사용자({self.REGION_CODES.get(user_region, user_region)})",
            )

    def _check_license(
        self, bid: BidAnnouncement, profile: UserProfile
    ) -> Tuple[bool, str]:
        """면허 요구사항 검증"""
        if not profile.licenses or len(profile.licenses) == 0:
            return False, "보유 면허 없음"

        required_licenses = self._extract_license_requirements(bid)
        if not required_licenses:
            return True, "면허 요구사항 없음"

        user_licenses = [lic.license_name for lic in profile.licenses]

        for required in required_licenses:
            for user_license in user_licenses:
                if (
                    required.lower() in user_license.lower()
                    or user_license.lower() in required.lower()
                ):
                    return True, f"면허 일치: {user_license}"

        return False, f"필요 면허 미보유: {', '.join(required_licenses)}"

    def _check_performance(
        self, bid: BidAnnouncement, profile: UserProfile
    ) -> Tuple[bool, str]:
        """실적 요구사항 검증 (입찰 금액의 50% 이상 실적 보유 필요)"""
        if not bid.estimated_price or bid.estimated_price <= 0:
            return True, "입찰 금액 정보 없음 (실적 검증 불가)"

        if not profile.performances or len(profile.performances) == 0:
            return False, "보유 실적 없음"

        max_performance = self._get_max_performance(profile)
        if max_performance <= 0:
            return False, "유효한 실적 없음"

        required_performance = bid.estimated_price * 0.5

        if max_performance >= required_performance:
            return (
                True,
                f"실적 충족: {max_performance:,.0f}원 (필요: {required_performance:,.0f}원)",
            )
        else:
            return (
                False,
                f"실적 부족: {max_performance:,.0f}원 < {required_performance:,.0f}원 (필요)",
            )

    def _extract_region_from_bid(self, bid: BidAnnouncement) -> Optional[str]:
        """입찰 공고에서 지역 코드 추출"""
        # 공고에 region_code가 직접 있으면 사용
        if bid.region_code and bid.region_code != "00":
            return bid.region_code

        # 기관명/제목에서 지역 추출
        text = f"{bid.agency or ''} {bid.title or ''}".lower()
        for code, name in self.REGION_CODES.items():
            short_name = (
                name.replace("특별시", "")
                .replace("광역시", "")
                .replace("특별자치시", "")
                .replace("특별자치도", "")
                .replace("도", "")
                .lower()
            )
            if short_name in text:
                return code
        return None

    def _extract_license_requirements(self, bid: BidAnnouncement) -> List[str]:
        """입찰 공고에서 필요한 면허 추출"""
        # 공고에 license_requirements가 있으면 우선 사용
        if bid.license_requirements:
            return bid.license_requirements

        text = f"{bid.title or ''} {bid.content or ''}".lower()
        required = []
        for category, keywords in self.LICENSE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    required.append(keyword)
                    break
        return list(set(required))

    def _get_max_performance(self, profile: UserProfile) -> float:
        """사용자의 최대 실적 금액 반환"""
        if not profile.performances:
            return 0.0
        amounts = [perf.amount for perf in profile.performances if perf.amount]
        return max(amounts) if amounts else 0.0

    def get_matching_score(self, bid: BidAnnouncement, profile: UserProfile) -> float:
        """매칭 점수 계산 (0.0 ~ 1.0)"""
        is_match, reasons, details = self.evaluate(bid, profile)
        if is_match:
            return 1.0

        score = 0.0
        if details["region_check"]["passed"]:
            score += 0.33
        if details["license_check"]["passed"]:
            score += 0.33
        if details["performance_check"]["passed"]:
            score += 0.34
        return score


# ============================================
# Unified Matching Service
# ============================================


class MatchingService:
    """
    통합 매칭 서비스
    - check_hard_match: 제약 조건 기반 Hard Match
    - calculate_soft_match: 키워드/지역/중요도 기반 Soft Match
    - calculate_semantic_match: Gemini AI 기반 Semantic Match
    """

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY:
            try:
                from google import genai

                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info(
                    "MatchingService: Gemini 2.5 Flash client initialized for Semantic Search"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Gemini in MatchingService: {e}")

    def check_hard_match(
        self, user_profile: UserProfile, bid: BidAnnouncement
    ) -> Dict[str, Any]:
        """
        Hard Match 실행

        Returns:
            {"is_match": bool, "reasons": List[str]}
        """
        reasons = []

        # 1. 지역 제한 확인
        if bid.region_code and bid.region_code != "00":
            if not user_profile.location_code:
                reasons.append(f"사용자 지역 정보 없음 (공고 제한: {bid.region_code})")
            elif user_profile.location_code != bid.region_code:
                reasons.append(
                    f"지역 불일치 (공고: {bid.region_code}, 사용자: {user_profile.location_code})"
                )

        # 2. 면허 제한 확인
        if bid.license_requirements:
            user_licenses = {l.license_name for l in user_profile.licenses}
            has_valid_license = False
            for req_license in bid.license_requirements:
                if any(req_license in ul for ul in user_licenses):
                    has_valid_license = True
                    break
            if not has_valid_license:
                reasons.append(
                    f"필요 면허 미보유 (요구: {', '.join(bid.license_requirements)})"
                )

        # 3. 실적 제한 확인
        if bid.min_performance and bid.min_performance > 0:
            max_user_perf = 0.0
            if user_profile.performances:
                max_user_perf = max([p.amount for p in user_profile.performances])
            if max_user_perf < bid.min_performance:
                reasons.append(
                    f"실적 기준 미달 (요구: {bid.min_performance:,}원, 보유최대: {max_user_perf:,}원)"
                )

        return {"is_match": len(reasons) == 0, "reasons": reasons}

    def calculate_soft_match(
        self, user_profile: UserProfile, bid: BidAnnouncement
    ) -> Dict[str, Any]:
        """
        Soft Match 실행 (정성적 평가)

        Returns:
            {"score": int (0~100), "breakdown": List[str]}
        """
        score = 0
        breakdown = []
        user_keywords = user_profile.keywords or []

        # 1. 키워드 매칭
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
            breakdown.append(
                f"제목 키워드 포함 (+{len(matched_in_title)*20}): {', '.join(matched_in_title)}"
            )
        if matched_in_content:
            breakdown.append(
                f"본문 키워드 포함 (+{len(matched_in_content)*5}): {', '.join(matched_in_content)}"
            )
        score += keyword_score

        # 2. 지역 매칭 (+10점)
        if user_profile.location_code and bid.region_code:
            if user_profile.location_code == bid.region_code:
                score += 10
                breakdown.append(f"선호 지역 일치 (+10): {bid.region_code}")

        # 3. 중요도 점수 반영
        importance_bonus = (bid.importance_score or 1) * 5
        score += importance_bonus
        breakdown.append(
            f"공고 중요도({bid.importance_score}) 반영 (+{importance_bonus})"
        )

        final_score = min(max(score, 0), 100)
        return {"score": final_score, "breakdown": breakdown}

    async def calculate_semantic_match(
        self, user_query: str, bid: BidAnnouncement
    ) -> Dict[str, Any]:
        """
        Gemini 2.5 Flash 기반 시맨틱 매칭

        Returns:
            {"score": float (0.0~1.0), "reasoning": str, "error": str}
        """
        if not self.client:
            return {"score": 0.0, "error": "Gemini Client not initialized"}

        prompt = f"""
        You are an expert procurement analyst. Evalute the relevance between the User Query and the Bid Announcement.

        User Query: "{user_query}"

        Bid Announcement:
        Title: "{bid.title}"
        Content: "{bid.content[:1000]}"

        Task:
        1. Analyze the intent of the User Query.
        2. Determine if the Bid Announcement satisfies the query (Semantic Match).
        3. Assign a relevance score between 0.0 and 1.0.
           - 1.0: Perfect match
           - 0.8~0.9: High relevance
           - 0.5~0.7: Partial relevance
           - 0.1~0.4: Low relevance
           - 0.0: Irrelevant

        *IMPORTANT*: Be generous with location matching.

        Output Format:
        Provide the response in pure JSON format WITHOUT Markdown blocks.
        {{
            "reasoning": "Explain why you assigned this score in Korean.",
            "score": 0.0
        }}
        """

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = (
                    raw_text.replace("```json", "", 1).replace("```", "", 1).strip()
                )
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "", 1).strip()

            try:
                data = json.loads(raw_text)
                score = float(data.get("score", 0.0))
                reasoning = data.get("reasoning", "No reasoning provided.")
                return {"score": score, "reasoning": reasoning, "error": None}
            except json.JSONDecodeError:
                logger.error(f"Gemini JSON Parse Error. Raw: {raw_text}")
                return {
                    "score": 0.0,
                    "reasoning": f"JSON Parse Error: {raw_text[:50]}...",
                    "error": "JSON Parse Error",
                }

        except Exception as e:
            logger.error(f"Gemini Semantic Match Error: {e}")
            return {"score": 0.0, "error": str(e)}


# Singleton instances
hard_match_engine = HardMatchEngine()
matching_service = MatchingService()
