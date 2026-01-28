import asyncio
import os
import sys
import httpx
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.crawler_service import g2b_crawler

async def debug_crawl():
    print("=== Direct G2B API Debug Test ===")
    print(f"Time: {datetime.now()}")
    print(f"API Endpoint: {settings.G2B_API_ENDPOINT}")
    
    # Check API Key
    api_key = os.getenv("G2B_API_KEY", settings.G2B_API_KEY)
    print(f"API Key Length: {len(api_key)}")

    # 1. Fetch raw data
    params = {
        "serviceKey": api_key,
        "numOfRows": 100,
        "pageNo": 1,
        "inqryDiv": "1",
        "type": "json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"Sending request to G2B...")
            response = await client.get(settings.G2B_API_ENDPOINT, params=params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error Response: {response.text[:500]}")
                return

            data = response.json()
            
            # 2. Inspect Body
            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            print(f"✅ Raw Data Items Count: {len(items)}")
            
            if len(items) > 0:
                print("--- Sample Item ---")
                sample = items[0]
                print(f"Title: {sample.get('bidNtceNm')}")
                print(f"Agency: {sample.get('ntceInsttNm')}")
            
            # 3. Test Parsing
            announcements = g2b_crawler._parse_api_response(data)
            print(f"✅ Parsed Announcements Count: {len(announcements)}")
            
            # 4. Test Filtering
            # Bypass dynamic keywords for this check
            exclude_keywords = g2b_crawler.DEFAULT_EXCLUDE_KEYWORDS
            filtered = [a for a in announcements if g2b_crawler._should_notify(a, exclude_keywords)]
            print(f"✅ Filtered (Include Keywords matched) Count: {len(filtered)}")

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_crawl())
