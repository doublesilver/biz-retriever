"""
G2BCrawlerService fetch_new_announcements 단위 테스트
- 정상 API 응답 (공고 수집 + 필터링)
- API 에러 (resultCode != "00")
- HTTP 에러
- 빈 응답
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.crawler_service import G2BCrawlerService


@pytest.fixture
def service():
    return G2BCrawlerService()


class TestFetchNewAnnouncements:
    """fetch_new_announcements 테스트"""

    async def test_successful_fetch_with_filter(self, service):
        """정상 API 호출 → 필터링된 결과 반환"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "items": [
                        {
                            "bidNtceNm": "구내식당 위탁운영 공고",
                            "bidNtceDtl": "식당 운영 업체 모집",
                            "ntceInsttNm": "서울시청",
                            "bidNtceDt": "202601201000",
                            "bidClseDt": "202601271800",
                            "bidNtceUrl": "https://g2b.go.kr/test",
                            "presmptPrce": "500000000",
                        },
                        {
                            "bidNtceNm": "건설 공사 입찰",
                            "bidNtceDtl": "건물 건설",
                            "ntceInsttNm": "건설부",
                            "bidNtceDt": "202601201000",
                            "bidClseDt": None,
                            "bidNtceUrl": "https://g2b.go.kr/test2",
                            "presmptPrce": "100000000",
                        },
                    ]
                },
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            with patch.object(service, "_scrape_attachments", AsyncMock(return_value=None)):
                result = await service.fetch_new_announcements()

        # "구내식당 위탁운영" 매칭, "건설 공사" 미매칭
        assert len(result) >= 1
        assert result[0]["title"] == "구내식당 위탁운영 공고"

    async def test_api_business_error(self, service):
        """API resultCode != "00" → 빈 리스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "header": {"resultCode": "99", "resultMsg": "SERVICE_ERROR"},
                "body": {"items": []},
            }
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_new_announcements()

        assert result == []

    async def test_http_error(self, service):
        """HTTP 에러 → 빈 리스트"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.crawler_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.fetch_new_announcements()

        assert result == []

    async def test_empty_items(self, service):
        """빈 아이템 → 빈 리스트"""
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
            result = await service.fetch_new_announcements()

        assert result == []

    async def test_with_from_date(self, service):
        """from_date 파라미터 포함"""
        from datetime import datetime

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
            result = await service.fetch_new_announcements(
                from_date=datetime(2026, 1, 20)
            )

        assert result == []
        # Verify from_date was included in params
        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert "inqryBgnDt" in params
