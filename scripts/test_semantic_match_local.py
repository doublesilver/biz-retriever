import asyncio
import sys
import os
from types import SimpleNamespace

# Add project root to path
sys.path.append(os.getcwd())
# Force UTF-8 for Windows console/redirection
sys.stdout.reconfigure(encoding='utf-8')

# Mock settings before importing app modules
from unittest.mock import patch

# Mock Logger
import logging
logging.basicConfig(level=logging.INFO)

# Mock BidAnnouncement
class MockBid:
    def __init__(self, id, title, content):
        self.id = id
        self.title = title
        self.content = content

async def main():
    print("🚀 Starting Local Semantic Match Test...")

    # Hardcoded Key for Local Test
    API_KEY = "AIzaSyAGbYPKbY_5kwQ3ew-b9rARIUcroybjyQQ"
    
    # Patch settings
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.GEMINI_API_KEY = API_KEY
        
        # Import Service (it initializes client on import/init)
        # We need to make sure the import happens AFTER patching if possible, 
        # or we patch the instance.
        
        from app.services.matching_service import MatchingService
        
        service = MatchingService()
        # Force client init if it failed due to missing env var previously
        if not service.client:
             from google import genai
             service.client = genai.Client(api_key=API_KEY)
             print("✅ Client manually initialized with key.")

        # Test Case 1: Relevant
        query = "제주도 전기 공사"
        bid1 = MockBid(
            id=1, 
            title="[긴급] 제주시 동부지구 전기 배선 공사 입찰 공고", 
            content="제주시 구좌읍 일대 전기 배선 및 변압기 교체 공사를 진행합니다. 참여 자격은 전기공사업 면허 보유 업체..."
        )
        
        print(f"\n🧪 Test 1: Query='{query}' vs Title='{bid1.title}'")
        result1 = await service.calculate_semantic_match(query, bid1)
        
        with open("test_result_final.txt", "w", encoding="utf-8") as f:
            f.write(f"Result 1: {result1}\n")
        
        # Test Case 2: Irrelevant
        bid2 = MockBid(
            id=2, 
            title="서울 강남구 초등학교 급식 식자재 납품", 
            content="서울 강남구 소재 초등학교 급식용 유기농 식자재 납품 업체를 모집합니다."
        )
        print(f"\n🧪 Test 2: Query='{query}' vs Title='{bid2.title}'")
        result2 = await service.calculate_semantic_match(query, bid2)
        
        with open("test_result_final.txt", "a", encoding="utf-8") as f:
            f.write(f"Result 2: {result2}\n")

if __name__ == "__main__":
    asyncio.run(main())
