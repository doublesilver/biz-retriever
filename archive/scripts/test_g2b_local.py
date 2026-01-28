import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

G2B_API_KEY = os.getenv("G2B_API_KEY")
G2B_API_ENDPOINT = os.getenv("G2B_API_ENDPOINT", "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo")

def test_api():
    print("=== G2B API Key Test ===")
    
    if not G2B_API_KEY:
        print("[ERROR] G2B_API_KEY is missing in .env")
        return

    print(f"Key: {G2B_API_KEY[:10]}... (masked)")
    print(f"Endpoint: {G2B_API_ENDPOINT}")

    params = {
        "serviceKey": G2B_API_KEY,
        "numOfRows": 1,
        "pageNo": 1,
        "inqryDiv": "1",
        "type": "json",
        "inqryBgnDt": (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    }

    try:
        print("\nSending request...")
        response = requests.get(G2B_API_ENDPOINT, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[ERROR] API Request Failed: {response.text}")
            return

        try:
            data = response.json()
            header = data.get("response", {}).get("header", {})
            result_code = header.get("resultCode")
            result_msg = header.get("resultMsg")
            
            print(f"Result Code: {result_code}")
            print(f"Result Msg: {result_msg}")

            if result_code == "00":
                print("\n[SUCCESS] API Key is VALID and working!")
                items = data.get("response", {}).get("body", {}).get("items", [])
                if items:
                    print(f"Sample Bid: {items[0].get('bidNtceNm')}")
                else:
                    print("No items found, but auth successful.")
            else:
                print(f"\n[FAIL] API Error: {result_msg}")
                if result_code == "30":
                    print("-> SERVICE KEY IS NOT REGISTERED ERROR. 키가 등록되지 않았거나 동기화 지연.")
                elif result_code == "20":
                    print("-> SERVICE ACCESS DENIED.")

        except json.JSONDecodeError:
            print("[ERROR] Failed to decode JSON. Raw response:")
            print(response.text[:200])

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    test_api()
    input("\nPress Enter to exit...")
