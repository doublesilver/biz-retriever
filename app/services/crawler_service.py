"""
G2B 크롤러 서비스
나라장터(G2B) 공공데이터 API를 통해 입찰 공고를 수집하고 필터링합니다.
"""
from datetime import datetime
from typing import List, Dict, Optional
import httpx
from app.core.config import settings
from app.schemas.bid import BidAnnouncementCreate


class G2BCrawlerService:
    """
    G2B (나라장터) 크롤러 서비스
    공공데이터포털 API를 활용한 입찰 공고 수집
    """
    
    # 필터링 키워드 (SPEC.md 기준)
    INCLUDE_KEYWORDS_CONCESSION = [
        "구내식당", "사용수익허가", "위탁운영", "식음료", "클럽하우스",
        "장례식장", "급식", "식당운영", "카페운영"
    ]
    
    INCLUDE_KEYWORDS_FLOWER = [
        "화환", "연간단가", "취임식", "행사", "꽃", "근조", "경조사"
    ]
    
    EXCLUDE_KEYWORDS = [
        "폐기물", "단순공사", "설계용역", "철거", "해체"
    ]
    
    def __init__(self):
        self.api_key = settings.G2B_API_KEY
        self.api_endpoint = settings.G2B_API_ENDPOINT
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_new_announcements(self, from_date: Optional[datetime] = None) -> List[Dict]:
        """
        G2B API에서 새로운 입찰 공고를 가져옵니다.
        
        Args:
            from_date: 검색 시작 날짜 (기본값: 오늘)
        
        Returns:
            필터링된 입찰 공고 리스트
        """
        # API 요청 파라미터 구성
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 100,
            "pageNo": 1,
            "inqryDiv": "1",  # 입찰공고
            "type": "json",
        }
        
        if from_date:
            params["inqryBgnDt"] = from_date.strftime("%Y%m%d")
        
        try:
            # G2B API 호출
            response = await self.client.get(self.api_endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 데이터 파싱 및 필터링
            announcements = self._parse_api_response(data)
            filtered = [a for a in announcements if self._should_notify(a)]
            
            return filtered
        
        except Exception as e:
            # 에러 로깅 (추후 Sentry 연동)
            print(f"G2B API 에러: {e}")
            return []
    
    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """
        G2B API 응답을 파싱하여 표준 형식으로 변환
        
        Args:
            data: API 응답 데이터
        
        Returns:
            파싱된 공고 리스트
        """
        announcements = []
        items = data.get("response", {}).get("body", {}).get("items", [])
        
        for item in items:
            announcement = {
                "title": item.get("bidNtceNm", ""),
                "content": item.get("bidNtceDtl", ""),
                "agency": item.get("ntceInsttNm", ""),
                "posted_at": self._parse_datetime(item.get("bidNtceDt")),
                "deadline": self._parse_datetime(item.get("bidClseDt")),
                "url": item.get("bidNtceUrl", ""),
                "estimated_price": float(item.get("presmptPrce", 0) or 0),
                "source": "G2B",
            }
            announcements.append(announcement)
        
        return announcements
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """날짜 문자열을 datetime으로 변환 (G2B 형식: YYYYMMDDHHmm)"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d%H%M")
        except:
            return None
    
    def _should_notify(self, announcement: Dict) -> bool:
        """
        공고가 알림 대상인지 판단 (스마트 필터링)
        
        Args:
            announcement: 공고 정보
        
        Returns:
            True if 알림 대상, False otherwise
        """
        title = announcement["title"].lower()
        content = announcement.get("content", "").lower()
        full_text = f"{title} {content}"
        
        # 제외 키워드 체크
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword in full_text:
                return False
        
        # 포함 키워드 체크
        matched_keywords = []
        all_include_keywords = (
            self.INCLUDE_KEYWORDS_CONCESSION + self.INCLUDE_KEYWORDS_FLOWER
        )
        
        for keyword in all_include_keywords:
            if keyword in full_text:
                matched_keywords.append(keyword)
        
        # 키워드 매칭 저장
        announcement["keywords_matched"] = matched_keywords
        
        # 최소 1개 이상의 키워드 매칭 필요
        return len(matched_keywords) > 0
    
    def calculate_importance_score(self, announcement: Dict) -> int:
        """
        중요도 점수 산출 (1~3)
        
        Args:
            announcement: 공고 정보
        
        Returns:
            중요도 점수 (1: 낮음, 2: 중간, 3: 높음)
        """
        score = 1
        title = announcement["title"].lower()
        keywords = announcement.get("keywords_matched", [])
        estimated_price = announcement.get("estimated_price", 0)
        
        # 핵심 키워드 가중치
        high_value_keywords = ["구내식당", "위탁운영", "장례식장", "클럽하우스"]
        if any(k in title for k in high_value_keywords):
            score += 1
        
        # 금액 가중치
        if estimated_price >= 100_000_000:  # 1억 이상
            score += 1
        
        # 키워드 개수 가중치
        if len(keywords) >= 3:
            score += 1
        
        return min(score, 3)  # 최대 3점
    
    async def close(self):
        """HTTP 클라이언트 종료"""
        await self.client.aclose()


# 싱글톤 인스턴스
g2b_crawler = G2BCrawlerService()
