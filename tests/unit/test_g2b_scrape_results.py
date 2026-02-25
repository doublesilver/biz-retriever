"""
G2BCrawlerService 추가 커버리지 테스트
- fetch_opening_results (정상, API 에러, 예외, null 필드, from_date)
- _scrape_attachments (빈 URL, non-200, 링크 없음, 큰 파일, 예외)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.crawler_service import G2BCrawlerService


@pytest.fixture
def service():
    return G2BCrawlerService()


class TestFetchOpeningResults:
    """fetch_opening_results 테스트"""

    async def test_successful_fetch(self, service):
        """정상 개찰 결과"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": [
                        {
                            "bidNtceNo": "20260120001",
                            "bidNtceNm": "구내식당",
                            "ntceInsttNm": "서울시",
                            "sucsfutlEntrpsNm": "A업체",
                            "sucsfutlAmt": "500000000",
                            "baseAmt": "600000000",
                            "presmptPrce": "550000000",
                            "bidEntrpsCnt": "5",
                            "opengDt": "202601201400",
                        }
                    ]
                },
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_opening_results()

        assert len(result) == 1
        assert result[0]["bid_number"] == "20260120001"
        assert result[0]["winning_price"] == 500000000.0
        assert result[0]["participant_count"] == 5

    async def test_with_from_date(self, service):
        """from_date 포함"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": []},
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_opening_results(from_date=datetime(2026, 1, 20))

        assert result == []
        params = mock_client.get.call_args.kwargs.get("params", {})
        assert "inqryBgnDt" in params

    async def test_api_error(self, service):
        """API 비즈니스 에러"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "99"},
                "body": {"items": []},
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_opening_results()
        assert result == []

    async def test_exception(self, service):
        """예외 시 빈 리스트"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("fail"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_opening_results()
        assert result == []

    async def test_null_fields(self, service):
        """Null 필드 안전 처리"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": [
                        {
                            "bidNtceNo": "001",
                            "bidNtceNm": "공고",
                            "ntceInsttNm": "기관",
                            "sucsfutlEntrpsNm": None,
                            "sucsfutlAmt": None,
                            "baseAmt": None,
                            "presmptPrce": None,
                            "bidEntrpsCnt": None,
                            "opengDt": None,
                        }
                    ]
                },
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_opening_results()

        assert len(result) == 1
        assert result[0]["winning_company"] == "미정"
        assert result[0]["winning_price"] == 0.0


class TestScrapeAttachments:
    """_scrape_attachments 테스트"""

    async def test_empty_url(self, service):
        """빈 URL -> None"""
        result = await service._scrape_attachments("")
        assert result is None

    async def test_none_url(self, service):
        """None URL -> None"""
        result = await service._scrape_attachments(None)
        assert result is None

    async def test_non_200(self, service):
        """HTTP non-200 -> None"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service._scrape_attachments("https://g2b.go.kr/page")
        assert result is None

    async def test_no_target_links(self, service):
        """다운로드 링크 없음 -> None"""
        html = '<html><body><a href="/normal-page">링크</a></body></html>'
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_resp.url = "https://g2b.go.kr/page"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service._scrape_attachments("https://g2b.go.kr/page")
        assert result is None

    async def test_file_too_large(self, service):
        """10MB 초과 파일 -> None"""
        html = '<html><body><a href="/files/doc.pdf">문서.pdf</a></body></html>'
        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.text = html
        page_resp.url = "https://g2b.go.kr/page"

        head_resp = MagicMock()
        head_resp.headers = {"content-length": str(20 * 1024 * 1024)}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=page_resp)
        mock_client.head = AsyncMock(return_value=head_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service._scrape_attachments("https://g2b.go.kr/page")
        assert result is None

    async def test_exception_returns_none(self, service):
        """예외 -> None"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("boom"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service._scrape_attachments("https://g2b.go.kr/page")
        assert result is None

    async def test_successful_download(self, service):
        """파일 다운로드 + 텍스트 추출 성공"""
        html = '<html><body><a href="https://g2b.go.kr/files/doc.pdf">문서.pdf</a></body></html>'
        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.text = html
        page_resp.url = "https://g2b.go.kr/page"

        head_resp = MagicMock()
        head_resp.headers = {"content-length": "1024"}

        file_resp = MagicMock()
        file_resp.content = b"fake pdf"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[page_resp, file_resp])
        mock_client.head = AsyncMock(return_value=head_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.file_service.file_service") as mock_fs:
                mock_fs.get_text_from_file = AsyncMock(return_value="추출 텍스트")
                result = await service._scrape_attachments("https://g2b.go.kr/page")

        assert result == "추출 텍스트"

    async def test_relative_link_resolution(self, service):
        """상대 링크 -> 절대 URL 변환"""
        html = '<html><body><a href="/download/file.hwp">파일.hwp</a></body></html>'
        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.text = html
        page_resp.url = "https://g2b.go.kr/detail/123"

        head_resp = MagicMock()
        head_resp.headers = {"content-length": "512"}

        file_resp = MagicMock()
        file_resp.content = b"fake hwp"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[page_resp, file_resp])
        mock_client.head = AsyncMock(return_value=head_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.file_service.file_service") as mock_fs:
                mock_fs.get_text_from_file = AsyncMock(return_value="hwp text")
                result = await service._scrape_attachments("https://g2b.go.kr/detail/123")

        assert result == "hwp text"
