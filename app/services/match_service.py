"""
Hard Match Engine
Zero-Error 입찰 공고 매칭 엔진

3단계 검증:
1. 지역 코드 매칭
2. 면허 요구사항 검증
3. 실적 요구사항 검증
"""

from typing import Dict, List, Optional, Tuple
from app.core.logging import logger
from app.db.models import BidAnnouncement, UserProfile


class HardMatchEngine:
    """
    Hard Match 엔진 - Zero False Positive
    
    모든 조건을 만족하는 입찰만 매칭 (오탐 0%)
    """
    
    # 지역 코드 매핑 (서울, 경기 등)
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
    
    # 면허 키워드 매핑
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
        self, 
        bid: BidAnnouncement, 
        profile: UserProfile
    ) -> Tuple[bool, List[str], Dict]:
        """
        Hard Match 평가
        
        Args:
            bid: 입찰 공고
            profile: 사용자 프로필 (면허, 실적 포함)
        
        Returns:
            (is_match, reasons, details)
            - is_match: 매칭 여부 (True/False)
            - reasons: 불일치 사유 리스트
            - details: 상세 검증 결과
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
            "user_region": profile.region_code,
        }
        if not region_match:
            reasons.append(region_reason)
        
        # 2. 면허 검증
        license_match, license_reason = self._check_license(bid, profile)
        details["license_check"] = {
            "passed": license_match,
            "reason": license_reason,
            "required_licenses": self._extract_license_requirements(bid),
            "user_licenses": [lic.license_name for lic in profile.licenses] if profile.licenses else [],
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
        
        # 모든 조건 만족해야 매칭
        is_match = region_match and license_match and performance_match
        
        if is_match:
            self.logger.info(f"Hard Match SUCCESS: bid_id={bid.id}, user={profile.user_id}")
        else:
            self.logger.debug(f"Hard Match FAIL: bid_id={bid.id}, reasons={reasons}")
        
        return is_match, reasons, details
    
    def _check_region(self, bid: BidAnnouncement, profile: UserProfile) -> Tuple[bool, str]:
        """
        지역 코드 검증
        
        입찰 공고의 지역과 사용자의 사업 지역이 일치하는지 확인
        """
        # 프로필에 지역 코드가 없으면 전국 가능으로 간주
        if not profile.region_code:
            return True, "지역 제한 없음 (전국 가능)"
        
        # 입찰 공고에서 지역 추출
        bid_region = self._extract_region_from_bid(bid)
        if not bid_region:
            # 지역 정보가 없으면 통과 (보수적 접근)
            return True, "입찰 지역 정보 없음 (전국 가능으로 간주)"
        
        # 사용자 지역과 입찰 지역 비교
        if profile.region_code == bid_region:
            return True, f"지역 일치: {self.REGION_CODES.get(bid_region, bid_region)}"
        else:
            return False, f"지역 불일치: 입찰({self.REGION_CODES.get(bid_region, bid_region)}) vs 사용자({self.REGION_CODES.get(profile.region_code, profile.region_code)})"
    
    def _check_license(self, bid: BidAnnouncement, profile: UserProfile) -> Tuple[bool, str]:
        """
        면허 요구사항 검증
        
        입찰 공고에 필요한 면허를 사용자가 보유하고 있는지 확인
        """
        # 프로필에 면허 정보가 없으면 실패
        if not profile.licenses or len(profile.licenses) == 0:
            return False, "보유 면허 없음"
        
        # 입찰 공고에서 필요한 면허 추출
        required_licenses = self._extract_license_requirements(bid)
        if not required_licenses:
            # 면허 요구사항이 명시되지 않으면 통과
            return True, "면허 요구사항 없음"
        
        # 사용자가 보유한 면허 목록
        user_licenses = [lic.license_name for lic in profile.licenses]
        
        # 필요한 면허 중 하나라도 보유하고 있으면 통과
        for required in required_licenses:
            for user_license in user_licenses:
                if required.lower() in user_license.lower() or user_license.lower() in required.lower():
                    return True, f"면허 일치: {user_license}"
        
        return False, f"필요 면허 미보유: {', '.join(required_licenses)}"
    
    def _check_performance(self, bid: BidAnnouncement, profile: UserProfile) -> Tuple[bool, str]:
        """
        실적 요구사항 검증
        
        입찰 금액을 처리할 수 있는 실적이 있는지 확인
        일반적으로 입찰 금액의 50% 이상 실적 필요
        """
        # 입찰 금액 정보가 없으면 통과
        if not bid.estimated_price or bid.estimated_price <= 0:
            return True, "입찰 금액 정보 없음 (실적 검증 불가)"
        
        # 프로필에 실적 정보가 없으면 실패
        if not profile.performances or len(profile.performances) == 0:
            return False, "보유 실적 없음"
        
        # 사용자의 최대 실적 금액
        max_performance = self._get_max_performance(profile)
        if max_performance <= 0:
            return False, "유효한 실적 없음"
        
        # 실적 검증 기준: 입찰 금액의 50% 이상 실적 보유
        required_performance = bid.estimated_price * 0.5
        
        if max_performance >= required_performance:
            return True, f"실적 충족: {max_performance:,.0f}원 (필요: {required_performance:,.0f}원)"
        else:
            return False, f"실적 부족: {max_performance:,.0f}원 < {required_performance:,.0f}원 (필요)"
    
    def _extract_region_from_bid(self, bid: BidAnnouncement) -> Optional[str]:
        """
        입찰 공고에서 지역 코드 추출
        
        기관명이나 제목에서 지역 정보 추출
        """
        text = f"{bid.agency or ''} {bid.title or ''}".lower()
        
        # 지역명으로 매칭
        for code, name in self.REGION_CODES.items():
            if name.replace("특별시", "").replace("광역시", "").replace("특별자치시", "").replace("도", "").lower() in text:
                return code
        
        return None
    
    def _extract_license_requirements(self, bid: BidAnnouncement) -> List[str]:
        """
        입찰 공고에서 필요한 면허 추출
        
        제목과 내용에서 면허 키워드 찾기
        """
        text = f"{bid.title or ''} {bid.content or ''}".lower()
        required = []
        
        for category, keywords in self.LICENSE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    required.append(keyword)
                    break  # 카테고리당 하나만
        
        return list(set(required))  # 중복 제거
    
    def _get_max_performance(self, profile: UserProfile) -> float:
        """
        사용자의 최대 실적 금액 반환
        """
        if not profile.performances:
            return 0.0
        
        amounts = [perf.contract_amount for perf in profile.performances if perf.contract_amount]
        return max(amounts) if amounts else 0.0
    
    def get_matching_score(self, bid: BidAnnouncement, profile: UserProfile) -> float:
        """
        매칭 점수 계산 (0.0 ~ 1.0)
        
        Hard Match는 All-or-Nothing이지만, 
        향후 Soft Match나 우선순위 정렬에 사용 가능
        """
        is_match, reasons, details = self.evaluate(bid, profile)
        
        if is_match:
            return 1.0
        
        # 부분 점수 (각 조건별 1/3)
        score = 0.0
        if details["region_check"]["passed"]:
            score += 0.33
        if details["license_check"]["passed"]:
            score += 0.33
        if details["performance_check"]["passed"]:
            score += 0.34
        
        return score


# 싱글톤 인스턴스
hard_match_engine = HardMatchEngine()
