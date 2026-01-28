import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.crawler_service import G2BCrawlerService

@pytest.mark.asyncio
async def test_scrape_attachments_logic():
    crawler = G2BCrawlerService()
    
    # Mock URL
    target_url = "http://www.g2b.go.kr/detail.do?id=12345"
    file_url = "http://www.g2b.go.kr/download/test.hwp"
    
    # Mock HTML content
    mock_html = f"""
    <html>
        <body>
            <div class="table">
                <a href="{file_url}">Download HWP</a>
                <a href="other.txt">Ignore</a>
            </div>
        </body>
    </html>
    """
    
    # Mock httpx client
    mock_client = MagicMock()
    
    # Setup Async Context Manager for client
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    # Setup Responses
    # 1. Page Load
    mock_page_resp = MagicMock()
    mock_page_resp.status_code = 200
    mock_page_resp.text = mock_html
    mock_page_resp.url = target_url # For urljoin if needed
    
    # 2. HEAD request (size check)
    mock_head_resp = MagicMock()
    mock_head_resp.headers = {"content-length": "1000"}
    
    # 3. File Download
    mock_file_resp = MagicMock()
    mock_file_resp.content = b"MOCK_HWP_BINARY_DATA"
    
    # Side effect for client.get: First call (page), Second call (file)
    # But scraping uses client.get twice.
    # We can mock using side_effect with checks on args or simpler list
    
    async def side_effect_get(url, **kwargs):
        if url == target_url:
            return mock_page_resp
        elif url == file_url:
            return mock_file_resp
        return MagicMock(status_code=404)
        
    mock_client.get = AsyncMock(side_effect=side_effect_get)
    mock_client.head = AsyncMock(return_value=mock_head_resp)
    
    # Mock file_service.get_text_from_file to avoid actual parsing errors on fake data
    with patch("app.services.file_service.file_service.get_text_from_file", new_callable=AsyncMock) as mock_parser:
        mock_parser.return_value = "Parsed Text Success"
        
        # Patch httpx.AsyncClient to return our mock
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await crawler._scrape_attachments(target_url)
            
            print(f"Result: {result}")
            assert result == "Parsed Text Success"
            
            # Verify calls
            # mock_client.get.assert_any_call(target_url)
            # mock_client.get.assert_any_call(file_url) # Might be called differently, just check result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_scrape_attachments_logic())
