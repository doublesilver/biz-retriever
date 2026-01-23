"""
온비드(Onbid) 크롤러 서비스
캠코(한국자산관리공사) 온비드 사이트에서 임대/매각 공고 수집
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
import re

from app.core.config import settings
from app.core.logging import logger


class OnbidCrawlerService:
    """
    온비드(Onbid) 크롤러 서비스
    캠코 온비드 사이트에서 임대/매각 공고를 수집합니다.

    지원 공고 유형:
    - 임대: 식당, 카페, 매점 등
    - 매각: 부동산 관련
    """

    # 베이스 URL
    BASE_URL = "https://www.onbid.co.kr"

    # 임대 공고 검색 URL (캠코 공매 시스템)
    RENTAL_SEARCH_URL = "https://www.onbid.co.kr/op/cta/cltaSearch/collateralTenderSearch.do"

    # 매각 공고 검색 URL
    SALE_SEARCH_URL = "https://www.onbid.co.kr/op/ppa/ppaSrch/ppaSearch.do"

    # 임대 타겟 키워드
    RENTAL_KEYWORDS = [
        "식당", "카페", "매점", "구내식당", "클럽하우스",
        "편의점", "휴게소", "푸드코트", "커피숍", "식음료",
        "위탁운영", "임대", "운영권"
    ]

    # 제외 키워드
    EXCLUDE_KEYWORDS = [
        "폐기물", "철거", "해체", "단순공사", "청소용역"
    ]

    # 우선 기관 (가중치 적용)
    PRIORITY_AGENCIES = [
        "한국도로공사", "한국철도공사", "인천국제공항공사",
        "한국공항공사", "한국토지주택공사", "서울교통공사"
    ]

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    async def fetch_rental_announcements(
        self,
        from_date: Optional[datetime] = None,
        max_pages: int = 5
    ) -> List[Dict]:
        """
        온비드에서 임대 공고를 수집합니다.

        Args:
            from_date: 검색 시작 날짜 (기본: 7일 전)
            max_pages: 최대 검색 페이지 수

        Returns:
            필터링된 임대 공고 리스트
        """
        if from_date is None:
            from_date = datetime.now() - timedelta(days=7)

        all_announcements = []

        try:
            for page in range(1, max_pages + 1):
                logger.info(f"온비드 임대 공고 크롤링: 페이지 {page}/{max_pages}")

                announcements = await self._fetch_page(page, from_date)

                if not announcements:
                    logger.info(f"페이지 {page}: 더 이상 공고 없음")
                    break

                # 필터링 적용
                filtered = [a for a in announcements if self._should_include(a)]
                all_announcements.extend(filtered)

                logger.info(f"페이지 {page}: {len(announcements)}건 수집, {len(filtered)}건 필터링 통과")

            # 중요도 점수 계산
            for announcement in all_announcements:
                announcement["importance_score"] = self._calculate_importance(announcement)

            logger.info(f"온비드 크롤링 완료: 총 {len(all_announcements)}건 수집")
            return all_announcements

        except Exception as e:
            logger.error(f"온비드 크롤링 실패: {e}", exc_info=True)
            return []

    async def _fetch_page(self, page: int, from_date: datetime) -> List[Dict]:
        """
        특정 페이지의 공고 목록을 가져옵니다.

        Args:
            page: 페이지 번호
            from_date: 검색 시작 날짜

        Returns:
            공고 리스트
        """
        announcements = []

        try:
            # POST 요청으로 검색 (온비드는 POST 방식 사용)
            params = {
                "currentPage": page,
                "rowCount": 20,
                "sortOrder": "ASC",
                "bidStartDtFrom": from_date.strftime("%Y-%m-%d"),
                "bidStartDtTo": datetime.now().strftime("%Y-%m-%d"),
                "tenderType": "01",  # 01: 임대
            }

            response = await self.client.post(
                self.RENTAL_SEARCH_URL,
                data=params,
                follow_redirects=True
            )

            if response.status_code != 200:
                logger.warning(f"온비드 응답 오류: {response.status_code}")
                return []

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # 공고 목록 테이블 파싱
            rows = soup.select("table.tb_type01 tbody tr")

            for row in rows:
                try:
                    announcement = self._parse_row(row)
                    if announcement:
                        announcements.append(announcement)
                except Exception as e:
                    logger.warning(f"행 파싱 실패: {e}")
                    continue

            return announcements

        except httpx.RequestError as e:
            logger.error(f"온비드 요청 실패: {e}")
            return []

    def _parse_row(self, row) -> Optional[Dict]:
        """
        테이블 행을 파싱하여 공고 정보를 추출합니다.

        Args:
            row: BeautifulSoup row element

        Returns:
            공고 정보 딕셔너리 또는 None
        """
        cells = row.find_all("td")
        if len(cells) < 5:
            return None

        # 제목 및 링크 추출
        title_cell = cells[1]
        title_link = title_cell.find("a")

        if not title_link:
            return None

        title = title_link.get_text(strip=True)
        detail_url = title_link.get("href", "")

        # 상세 URL 구성
        if detail_url and not detail_url.startswith("http"):
            detail_url = f"{self.BASE_URL}{detail_url}"

        # 기관명 추출
        agency = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        # 입찰 기간 추출
        period_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        deadline = self._parse_deadline(period_text)

        # 추정가 추출
        price_text = cells[4].get_text(strip=True) if len(cells) > 4 else "0"
        estimated_price = self._parse_price(price_text)

        return {
            "title": title,
            "content": title,  # 상세 내용은 별도 요청 필요
            "agency": agency,
            "posted_at": datetime.now(),
            "deadline": deadline,
            "url": detail_url,
            "estimated_price": estimated_price,
            "source": "Onbid",
            "keywords_matched": [],
        }

    def _parse_deadline(self, period_text: str) -> Optional[datetime]:
        """
        입찰 기간 텍스트에서 마감일을 추출합니다.

        Args:
            period_text: "2026-01-20 ~ 2026-01-25" 형식

        Returns:
            마감일 datetime 또는 None
        """
        try:
            # "~" 기준으로 분리하여 종료일 추출
            if "~" in period_text:
                end_date_str = period_text.split("~")[1].strip()
                return datetime.strptime(end_date_str[:10], "%Y-%m-%d")
            return None
        except (ValueError, IndexError):
            return None

    def _parse_price(self, price_text: str) -> float:
        """
        가격 텍스트를 숫자로 변환합니다.

        Args:
            price_text: "1,234,567원" 형식

        Returns:
            가격 (원)
        """
        try:
            # 숫자만 추출
            numbers = re.sub(r"[^\d]", "", price_text)
            return float(numbers) if numbers else 0.0
        except ValueError:
            return 0.0

    def _should_include(self, announcement: Dict) -> bool:
        """
        공고가 수집 대상인지 판단합니다.

        Args:
            announcement: 공고 정보

        Returns:
            True if 수집 대상
        """
        title = announcement.get("title", "").lower()
        content = announcement.get("content", "").lower()
        full_text = f"{title} {content}"

        # 제외 키워드 체크
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword in full_text:
                return False

        # 포함 키워드 체크
        matched_keywords = []
        for keyword in self.RENTAL_KEYWORDS:
            if keyword in full_text:
                matched_keywords.append(keyword)

        announcement["keywords_matched"] = matched_keywords

        # 최소 1개 이상의 키워드 매칭 필요
        return len(matched_keywords) > 0

    def _calculate_importance(self, announcement: Dict) -> int:
        """
        중요도 점수를 계산합니다 (1~3).

        Args:
            announcement: 공고 정보

        Returns:
            중요도 점수
        """
        score = 1
        title = announcement.get("title", "").lower()
        agency = announcement.get("agency", "")
        keywords = announcement.get("keywords_matched", [])
        estimated_price = announcement.get("estimated_price", 0)

        # 핵심 키워드 가중치
        high_value_keywords = ["구내식당", "위탁운영", "클럽하우스", "휴게소"]
        if any(k in title for k in high_value_keywords):
            score += 1

        # 우선 기관 가중치
        if any(agency_name in agency for agency_name in self.PRIORITY_AGENCIES):
            score += 1

        # 금액 가중치 (월 500만원 이상)
        if estimated_price >= 5_000_000:
            score += 1

        # 키워드 개수 가중치
        if len(keywords) >= 2:
            score += 1

        return min(score, 3)  # 최대 3점

    async def fetch_announcement_detail(self, url: str) -> Optional[Dict]:
        """
        공고 상세 정보를 가져옵니다.

        Args:
            url: 공고 상세 페이지 URL

        Returns:
            상세 정보 딕셔너리 또는 None
        """
        try:
            response = await self.client.get(url, follow_redirects=True)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # 상세 내용 추출
            content_div = soup.select_one("div.cont_box")
            content = content_div.get_text(strip=True) if content_div else ""

            # 첨부파일 목록 추출
            attachments = []
            file_links = soup.select("a.file_link")
            for link in file_links:
                attachments.append({
                    "name": link.get_text(strip=True),
                    "url": link.get("href", "")
                })

            return {
                "content": content,
                "attachments": attachments,
            }

        except Exception as e:
            logger.error(f"상세 정보 조회 실패: {e}")
            return None

    async def close(self):
        """HTTP 클라이언트 종료"""
        await self.client.aclose()


# 싱글톤 인스턴스
onbid_crawler = OnbidCrawlerService()
