import os
import httpx
import asyncio
from app.core.config import settings

async def check_env():
    print("=== Production Environment Check ===")
    print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
    print(f"G2B_API_ENDPOINT: {settings.G2B_API_ENDPOINT}")
    
    # Check API Key presence (don't print the whole key for security)
    api_key = os.getenv("G2B_API_KEY", settings.G2B_API_KEY)
    if not api_key:
        print("❌ G2B_API_KEY is MISSING or EMPTY!")
    else:
        print(f"✅ G2B_API_KEY is set (Length: {len(api_key)})")
        print(f"✅ G2B_API_KEY starts with: {api_key[:10]}...")

    # Check Network Connectivity to G2B
    print("\n=== Testing G2B API Connectivity ===")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Simple test call
            params = {
                "serviceKey": api_key,
                "numOfRows": 1,
                "pageNo": 1,
                "inqryDiv": "1",
                "type": "json"
            }
            response = await client.get(settings.G2B_API_ENDPOINT, params=params)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                result_code = data.get("response", {}).get("header", {}).get("resultCode")
                print(f"✅ API Response Received. ResultCode: {result_code}")
                if result_code != "00":
                    print(f"⚠️ API Error Message: {data.get('response', {}).get('header', {}).get('resultMsg')}")
            else:
                print(f"❌ API Request Failed. Status: {response.status_code}")
                print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Network/Request Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_env())
