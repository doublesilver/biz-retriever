"""
온비드(Onbid) 크롤러 서비스
임대 입찰 전용 크롤링 (Selenium 기반)
"""
from typing import List, Dict, Optional
from datetime import datetime


class OnbidCrawlerService:
    """
    온비드(Onbid) 크롤러 서비스
    임대 공고 전용 - Selenium으로 동적 페이지 크롤링
    """
    
    # 임대 타겟 키워드
    RENTAL_KEYWORDS = [
        "식당 임대", "카페 임대", "매점 임대", 
        "구내식당 입찰", "클럽하우스 임대"
    ]
    
    def __init__(self):
        self.base_url = "https://www.onbid.co.kr"
        # TODO: Selenium WebDriver 초기화 (Phase 2에서 구현)
        self.driver = None
    
    async def fetch_rental_announcements(self) -> List[Dict]:
        """
        온비드에서 임대 공고를 크롤링
        
        Returns:
            임대 공고 리스트
        """
        # Phase 2 Implementation Placeholder
        # 실제 구현 시 Selenium으로 온비드 사이트 크롤링
        print("온비드 크롤링 구현 예정 (Phase 2)")
        return []
    
    def _should_include(self, title: str, description: str) -> bool:
        """
        공고가 임대 타겟인지 판단
        
        Args:
            title: 공고 제목
            description: 공고 내용
        
        Returns:
            True if 임대 타겟
        """
        full_text = f"{title} {description}".lower()
        return any(keyword in full_text for keyword in self.RENTAL_KEYWORDS)


# 싱글톤 인스턴스
onbid_crawler = OnbidCrawlerService()
