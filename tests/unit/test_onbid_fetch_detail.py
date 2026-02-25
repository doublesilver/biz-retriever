"""
OnbidCrawlerService 추가 커버리지 테스트
- fetch_rental_announcements: 빈 페이지, 예외, 기본 from_date
- _fetch_page: non-200, request error
- fetch_announcement_detail: 성공, non-200, no content_div, 예외
- close
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.onbid_crawler import OnbidCrawlerService


@pytest.fixture
def crawler():
    """httpx client가 mock된 OnbidCrawlerService"""
    with patch("app.services.onbid_crawler.httpx.AsyncClient"):
        svc = OnbidCrawlerService()
        svc.client = AsyncMock()
        return svc


class TestFetchRentalEmpty:
    """fetch_rental_announcements 추가 케이스"""

    async def test_empty_first_page(self, crawler):
        """첫 페이지부터 빈 결과 -> 빈 리스트"""
        with patch.object(crawler, "_fetch_page", AsyncMock(return_value=[])):
            result = await crawler.fetch_rental_announcements(max_pages=3)
        assert result == []

    async def test_exception_returns_empty(self, crawler):
        """크롤링 중 예외 -> 빈 리스트"""
        with patch.object(crawler, "_fetch_page", AsyncMock(side_effect=Exception("boom"))):
            result = await crawler.fetch_rental_announcements()
        assert result == []

    async def test_default_from_date(self, crawler):
        """from_date=None -> 기본 7일 전"""
        with patch.object(crawler, "_fetch_page", AsyncMock(return_value=[])):
            result = await crawler.fetch_rental_announcements(from_date=None)
        assert result == []

    async def test_importance_score_calculated(self, crawler):
        """필터 통과 공고에 중요도 점수 부여"""
        ann = {
            "title": "구내식당 위탁운영",
            "content": "식당 운영",
            "agency": "한국도로공사",
            "posted_at": datetime.now(),
            "url": "https://onbid.co.kr/1",
            "estimated_price": 6000000,
            "source": "Onbid",
            "keywords_matched": [],
        }
        with patch.object(crawler, "_fetch_page", AsyncMock(side_effect=[[ann], []])):
            result = await crawler.fetch_rental_announcements(max_pages=2)
        assert len(result) >= 1
        assert "importance_score" in result[0]


class TestFetchPageErrors:
    """_fetch_page 에러 케이스"""

    async def test_non_200_response(self, crawler):
        """HTTP 500 -> 빈 리스트"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        crawler.client.post = AsyncMock(return_value=mock_resp)

        result = await crawler._fetch_page(1, datetime.now())
        assert result == []

    async def test_request_error(self, crawler):
        """httpx.RequestError -> 빈 리스트"""
        crawler.client.post = AsyncMock(side_effect=httpx.RequestError("Connection refused"))
        result = await crawler._fetch_page(1, datetime.now())
        assert result == []

    async def test_row_parse_error_skipped(self, crawler):
        """개별 행 파싱 실패 시 해당 행만 스킵"""
        html = """
        <table class="tb_type01">
            <tbody>
                <tr><td>too few</td></tr>
                <tr>
                    <td>1</td>
                    <td><a href="/detail/2">식당 임대</a></td>
                    <td>기관</td>
                    <td>2026-01-20 ~ 2026-01-25</td>
                    <td>1,000,000원</td>
                </tr>
            </tbody>
        </table>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        crawler.client.post = AsyncMock(return_value=mock_resp)

        result = await crawler._fetch_page(1, datetime.now())
        assert len(result) == 1


class TestFetchAnnouncementDetail:
    """fetch_announcement_detail 테스트"""

    async def test_success_with_content_and_files(self, crawler):
        """정상 조회 (내용 + 첨부파일)"""
        html = """
        <html>
            <div class="cont_box">상세 내용입니다</div>
            <a class="file_link" href="/files/doc.pdf">첨부1.pdf</a>
            <a class="file_link" href="/files/doc2.hwp">첨부2.hwp</a>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        crawler.client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_announcement_detail("https://onbid.co.kr/1")
        assert result is not None
        assert "상세 내용" in result["content"]
        assert len(result["attachments"]) == 2

    async def test_non_200_returns_none(self, crawler):
        """HTTP 404 -> None"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        crawler.client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_announcement_detail("https://onbid.co.kr/1")
        assert result is None

    async def test_no_content_div(self, crawler):
        """content_div 없는 페이지"""
        html = "<html><body>빈 페이지</body></html>"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        crawler.client.get = AsyncMock(return_value=mock_resp)

        result = await crawler.fetch_announcement_detail("https://onbid.co.kr/1")
        assert result is not None
        assert result["content"] == ""
        assert result["attachments"] == []

    async def test_exception_returns_none(self, crawler):
        """예외 -> None"""
        crawler.client.get = AsyncMock(side_effect=Exception("Network error"))
        result = await crawler.fetch_announcement_detail("https://onbid.co.kr/1")
        assert result is None


class TestClose:
    """close 메서드"""

    async def test_close_calls_aclose(self, crawler):
        """client.aclose 호출"""
        crawler.client.aclose = AsyncMock()
        await crawler.close()
        crawler.client.aclose.assert_awaited_once()
