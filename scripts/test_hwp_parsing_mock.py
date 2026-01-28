import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import io
from app.services.file_service import file_service

@pytest.mark.asyncio
async def test_parse_hwp_mock():
    # Mock UploadFile
    mock_file = MagicMock()
    mock_file.filename = "test.hwp"
    
    # Mock content (Async method)
    mock_file.read = AsyncMock(return_value=b"MOCK_HWP_CONTENT")
    
    with patch("olefile.isOleFile", return_value=True), \
         patch("olefile.OleFileIO") as MockOle:
        
        # Setup Mock Ole Object
        instance = MockOle.return_value
        instance.listdir.return_value = [["BodyText", "Section0"]]
        
        # Mock Stream (Compressed Data)
        mock_stream = MagicMock()
        # Zlib compressed "Hello World" (utf-16le)
        # "Hello World" in utf-16le is:
        # b'\xff\xfeH\x00e\x00l\x00l\x00o\x00 \x00W\x00o\x00r\x00l\x00d\x00'
        # We need to compress this.
        import zlib
        original_text = "Hello World"
        encoded_text = original_text.encode('utf-16le')
        compressed_data = zlib.compress(encoded_text)
        
        mock_stream.read.return_value = compressed_data
        instance.openstream.return_value = mock_stream
        
        # Execute
        result = await file_service.parse_hwp(mock_file)
        
        # Verify
        print(f"Result: {result}")
        assert "Hello World" in result
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_parse_hwp_mock())
