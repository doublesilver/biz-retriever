import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.onbid_crawler import OnbidCrawlerService
from datetime import datetime

@pytest.fixture
def onbid_crawler():
    return OnbidCrawlerService()

@pytest.fixture
def mock_rental_html():
    return """
    <table class="tb_type01">
        <tbody>
            <tr>
                <td>1</td>
                <td><a href="/detail/123">서울대병원 구내식당 위탁운영</a></td>
                <td>서울대학교병원</td>
                <td>2026-01-20 ~ 2026-01-30</td>
                <td>150,000,000원</td>
                <td>진행중</td>
            </tr>
            <tr>
                <td>2</td>
                <td><a href="/detail/456">폐기물 처리 용역</a></td>
                <td>환경공단</td>
                <td>2026-01-22 ~ 2026-01-25</td>
                <td>50,000,000원</td>
                <td>진행중</td>
            </tr>
        </tbody>
    </table>
    """

@pytest.mark.asyncio
async def test_fetch_rental_announcements(onbid_crawler, mock_rental_html):
    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_rental_html
    
    onbid_crawler.client.post = AsyncMock(return_value=mock_response)
    
    results = await onbid_crawler.fetch_rental_announcements(max_pages=1)
    
    assert len(results) == 1  # Keywords filtering should exclude '폐기물'
    bid = results[0]
    assert bid["title"] == "서울대병원 구내식당 위탁운영"
    assert bid["agency"] == "서울대학교병원"
    assert bid["estimated_price"] == 150000000.0
    assert "구내식당" in bid["keywords_matched"]
    assert "위탁운영" in bid["keywords_matched"]

@pytest.mark.asyncio
async def test_should_include(onbid_crawler):
    # Case 1: Target Keyword
    bid1 = {"title": "카페 위탁 운영", "content": ""}
    assert onbid_crawler._should_include(bid1) is True
    
    # Case 2: Exclude Keyword
    bid2 = {"title": "건물 철거 공사", "content": ""}
    assert onbid_crawler._should_include(bid2) is False
    
    # Case 3: No Keyword
    bid3 = {"title": "일반 사무용품 구매", "content": ""}
    assert onbid_crawler._should_include(bid3) is False

def test_parse_price(onbid_crawler):
    assert onbid_crawler._parse_price("150,000,000원") == 150000000.0
    assert onbid_crawler._parse_price("금액미상") == 0.0

def test_calculate_importance(onbid_crawler):
    # High Score (Keyword + Agency + Price)
    bid_high = {
        "title": "구내식당 위탁운영",
        "agency": "한국도로공사",
        "estimated_price": 10000000,
        "keywords_matched": ["구내식당", "위탁운영"]
    }
    assert onbid_crawler._calculate_importance(bid_high) == 3
    
    # Low Score
    bid_low = {
        "title": "작은 매점",
        "agency": "기타기관",
        "estimated_price": 100000,
        "keywords_matched": ["매점"]
    }
    assert onbid_crawler._calculate_importance(bid_low) == 1
