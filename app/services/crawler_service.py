"""
G2B 크롤러 서비스
나라장터(G2B) 공공데이터 API를 통해 입찰 공고를 수집하고 필터링합니다.
"""
from datetime import datetime
from typing import List, Dict, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger

from app.schemas.bid import BidAnnouncementCreate
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class AsyncBytesFile:
    """Mock UploadFile for Bytes"""
    def __init__(self, data: bytes, filename: str):
        self.data = data
        self.filename = filename
        
    async def read(self):
        return self.data


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
    
    # Default Fallback (If DB fails or empty)
    DEFAULT_EXCLUDE_KEYWORDS = [
        "폐기물", "단순공사", "설계용역", "철거", "해체"
    ]
    
    def __init__(self):
        self.api_key = settings.G2B_API_KEY
        self.api_endpoint = settings.G2B_API_ENDPOINT
        # Celery 환경에서 Event Loop 충돌 방지를 위해 인스턴스 레벨 client 제거
        # self.client = httpx.AsyncClient(timeout=30.0)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True
    )
    async def fetch_new_announcements(
        self, 
        from_date: Optional[datetime] = None, 
        exclude_keywords: Optional[List[str]] = None,
        include_keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        G2B API에서 새로운 입찰 공고를 가져옵니다.
        """
        if exclude_keywords is None:
            exclude_keywords = self.DEFAULT_EXCLUDE_KEYWORDS
            
        # Default fallback if not provided (Phase 3 Migration Support)
        if include_keywords is None:
            include_keywords = self.INCLUDE_KEYWORDS_CONCESSION + self.INCLUDE_KEYWORDS_FLOWER

        # API 요청 파라미터 구성
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 100,  # [DEBUG] 수집 범위를 100개로 확대
            "pageNo": 1,
            "inqryDiv": "1",  # 입찰공고
            "type": "json",
        }
        
        if from_date:
            params["inqryBgnDt"] = from_date.strftime("%Y%m%d")
        
        try:
            logger.info(f"G2B API 요청 시작: {self.api_endpoint}, params={params}")
            
            # G2B API 호출 (매 요청마다 새로운 클라이언트 생성)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.api_endpoint, params=params)
                logger.info(f"G2B API 응답 상태: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
            
            # Check for API Header Error
            header = data.get("response", {}).get("header", {})
            if header.get("resultCode") != "00":
                logger.error(f"G2B API Business Error: {header}")
                return []

            # 데이터 파싱 및 필터링
            announcements = self._parse_api_response(data)
            logger.info(f"파싱된 전체 공고 개수: {len(announcements)}")
            
            # 필터링 적용
            filtered = [
                a for a in announcements 
                if self._should_notify(a, exclude_keywords, include_keywords)
            ]
            
            # Phase 1 Upgrade: Scrape Attachments for Filtered Items
            # Only scrape if it passes the initial keyword filter to save resources
            from app.services.file_service import file_service
            
            for item in filtered:
                try:
                    if item.get("url"):
                        logger.info(f"첨부파일 스크래핑 시도: {item['title']}")
                        # Scraping (Limit to 3 seconds connection, 10s read)
                        # MVP: We use simple scraping. 
                        # Real G2B might require JS rendering or cookies, but public link often works.
                        extracted_text = await self._scrape_attachments(item["url"])
                        if extracted_text:
                            item["attachment_content"] = extracted_text
                            logger.info(f"첨부파일 텍스트 추출 완료 ({len(extracted_text)} chars)")
                            
                            # Re-evalute keywords with attachment content?
                            # For Phase 1, we just store it.
                            # Phase 3 might use it for Hard Match.
                except Exception as e:
                    logger.error(f"첨부파일 처리 중 오류: {e}")

            for idx, item in enumerate(filtered):
                logger.info(f"[DEBUG G2B] {idx+1}. {item['title']} ({item['agency']}) - {item['estimated_price']:,}원")

            logger.info(f"필터링 후 알림 대상 개수: {len(filtered)}")
            
            return filtered

        except Exception as e:
            logger.error(f"공고 수집 중 오류 발생: {e}", exc_info=True)
            return []

        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True
    )
    async def fetch_opening_results(self, from_date: Optional[datetime] = None) -> List[Dict]:
        """
        G2B 개찰 결과 API에서 정보를 수집합니다.
        """
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 100,
            "pageNo": 1,
            "type": "json",
        }
        
        if from_date:
            # 개찰일자 범위 조회 (개찰일시: opengDt)
            # G2B 개찰결과 API는 보통 개찰일시 기준 조회
            params["inqryBgnDt"] = from_date.strftime("%Y%m%d0000")
            params["inqryEndDt"] = datetime.now().strftime("%Y%m%d2359")
        
        try:
            url = settings.G2B_RESULT_API_ENDPOINT
            logger.info(f"G2B 개찰결과 API 요청: {url}, params={params}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            header = data.get("response", {}).get("header", {})
            if header.get("resultCode") != "00":
                logger.error(f"G2B Result API Business Error: {header}")
                return []

            items = data.get("response", {}).get("body", {}).get("items", [])
            results = []
            for item in items:
                # BidResult 모델에 맞게 데이터 정규화
                results.append({
                    "bid_number": item.get("bidNtceNo", ""),
                    "title": item.get("bidNtceNm", ""),
                    "agency": item.get("ntceInsttNm", ""),
                    "winning_company": item.get("sucsfutlEntrpsNm", "") or "미정",
                    "winning_price": float(item.get("sucsfutlAmt", 0) or 0),
                    "base_price": float(item.get("baseAmt", 0) or 0),
                    "estimated_price": float(item.get("presmptPrce", 0) or 0),
                    "participant_count": int(item.get("bidEntrpsCnt", 0) or 0),
                    "bid_open_date": self._parse_datetime(item.get("opengDt")),
                    "raw_data": item
                })
            
            logger.info(f"수집된 개찰결과 개수: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"G2B 개찰결과 API 호출 실패: {e}")
            return []

    async def _scrape_attachments(self, url: str) -> Optional[str]:
        """
        URL에서 첨부파일(HWP, PDF)을 찾아 다운로드 및 텍스트 추출
        """
        if not url:
            return None
            
        try:
            from bs4 import BeautifulSoup
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # 1. Page Load
                response = await client.get(url)
                if response.status_code != 200:
                    return None
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 2. Find Attachment Links
                # G2B patterns vary, but usually inside a specific div or table.
                # We look for href ending with .hwp, .hwpx, .pdf
                # Or specific G2B download function calls (tricky).
                # Fallback: Look for any link with 'download' or 'file' in common structures.
                
                # Simple Heuristic: Look for hrefs ending with extensions
                target_exts = ['.hwp', '.hwpx', '.pdf']
                target_link = None
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    # G2B URLs might be relative or javascript:
                    # Often "javascript:fn_download(...)" -> Hard to parse without headless browser.
                    # But often external links or public data links correspond to direct downloads?
                    # Actually G2B external link usually redirects to detailed info.
                    # For Initial MVP, we try to find direct Http links.
                    
                    lower_href = href.lower()
                    if any(lower_href.endswith(ext) for ext in target_exts):
                        target_link = href
                        if not target_link.startswith("http"):
                            # Handle relative? G2B is complex.
                            # Start with base url?
                            # Use response.url.join(target_link)
                            from urllib.parse import urljoin
                            target_link = urljoin(str(response.url), target_link)
                        break
                
                # If no direct link found (likely JS), we skip for now (Phase 1 Limitation).
                # "Supreme Command" -> MVP criteria.
                # We log this limitation.
                if not target_link:
                    return None
                    
                # 3. Download File (Limit size)
                # Head request first?
                head_resp = await client.head(target_link)
                size = int(head_resp.headers.get("content-length", 0))
                if size > 10 * 1024 * 1024: # 10MB Limit
                    logger.warning(f"File too large: {size} bytes")
                    return None
                    
                file_resp = await client.get(target_link)
                content = file_resp.content
                
                # 4. Parse
                # Wrap content in AsyncFile-like object for file_service
                filename = target_link.split("/")[-1]
                if not any(filename.lower().endswith(ext) for ext in target_exts):
                    # Try to guess from content-type or just default to .hwp if magic?
                    pass
                
                mock_file = AsyncBytesFile(content, filename)
                from app.services.file_service import file_service
                return await file_service.get_text_from_file(mock_file)

        except Exception as e:
            logger.warning(f"Failed to scrape attachment from {url}: {e}")
            return None

    def _parse_api_response(self, data: Dict) -> List[Dict]:
        announcements = []
        items = data.get("response", {}).get("body", {}).get("items", [])
        
        for item in items:
            # posted_at은 DB에서 Not Null이므로 필수값 처리
            posted_at = self._parse_datetime(item.get("bidNtceDt"))
            if not posted_at:
                posted_at = datetime.now()

            announcement = {
                "title": item.get("bidNtceNm", ""),
                "content": item.get("bidNtceDtl", "") or "내용 없음", # Pydantic min_length=1 만족을 위해 기본값 설정
                "agency": item.get("ntceInsttNm", ""),
                "posted_at": posted_at,
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
        except (ValueError, TypeError):
            return None
    
    def _should_notify(self, announcement: Dict, exclude_keywords: List[str] = None, include_keywords: List[str] = None) -> bool:
        """
        공고가 알림 대상인지 판단 (스마트 필터링)
        """
        if exclude_keywords is None:
            exclude_keywords = self.DEFAULT_EXCLUDE_KEYWORDS
        
        if include_keywords is None:
             include_keywords = self.INCLUDE_KEYWORDS_CONCESSION + self.INCLUDE_KEYWORDS_FLOWER

        title = announcement["title"].lower()
        content = announcement.get("content", "").lower()
        full_text = f"{title} {content}"
        
        # 제외 키워드 체크
        for keyword in exclude_keywords:
            if keyword in full_text:
                return False
        
        # 포함 키워드 체크
        matched_keywords = []
        
        for keyword in include_keywords:
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
        """HTTP 클라이언트 종료 (더 이상 사용하지 않음)"""
        pass


# 싱글톤 인스턴스 제거됨 (DI 패턴 사용 권장)
# g2b_crawler = G2BCrawlerService() -> Removed for Dependency Injection
