
import asyncio
import httpx
from datetime import datetime
from app.core.config import settings

# Configuration (Dev/Test Environment)
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER = "qa_final_user"
TEST_PASSWORD = "TestPassword123!"
TEST_EMAIL = f"{TEST_USER}_{datetime.now().strftime('%H%M%S')}@example.com"

async def verify_full_cycle():
    print(f"🚀 Starting Full Cycle Verification on {BASE_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Registration
        print(f"\n[1] Registering User: {TEST_EMAIL}")
        try:
            resp = await client.post(f"{BASE_URL}/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": "QA Tester"
            })
            if resp.status_code == 201:
                print("   ✅ Registration Success")
            else:
                print(f"   ❌ Registration Failed: {resp.text}")
                return
        except Exception as e:
             print(f"   ❌ Error: {e}")
             return

        # 2. Login
        print("\n[2] Logging In")
        token = None
        try:
            resp = await client.post(f"{BASE_URL}/auth/login/access-token", data={
                "username": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                print("   ✅ Login Success")
            else:
                print(f"   ❌ Login Failed: {resp.text}")
                return
        except Exception as e:
             print(f"   ❌ Error: {e}")
             return
        
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Profile Update (Notification Settings)
        print("\n[3] Updating Profile (Notification Settings)")
        try:
            profile_data = {
                "company_name": "QA Corp",
                "slack_webhook_url": "https://hooks.slack.com/services/test/test/test",
                "is_slack_enabled": True
            }
            resp = await client.put(f"{BASE_URL}/profile/", json=profile_data, headers=headers)
            if resp.status_code == 200:
                print("   ✅ Profile Update Success")
            else:
                print(f"   ❌ Profile Update Failed: {resp.text}")
        except Exception as e:
             print(f"   ❌ Error: {e}")

        # 4. Trigger Crawl (Mock/Manual)
        print("\n[4] Triggering Manual Crawl")
        try:
            resp = await client.post(f"{BASE_URL}/crawler/trigger", headers=headers)
            if resp.status_code == 200:
                task_id = resp.json().get("task_id")
                print(f"   ✅ Crawl Triggered (Task: {task_id})")
            else:
                print(f"   ❌ Crawl Trigger Failed: {resp.text}")
        except Exception as e:
             print(f"   ❌ Error: {e}")

        # 5. Check Bid List (Wait slightly)
        print("\n[5] Checking Bid List")
        await asyncio.sleep(2)
        try:
            resp = await client.get(f"{BASE_URL}/bids/?skip=0&limit=5", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Handle Array vs Object
                items = data if isinstance(data, list) else data.get("items", [])
                print(f"   ✅ Bid List Retrieved: {len(items)} items")
            else:
                print(f"   ❌ Bid List Failed: {resp.text}")
        except Exception as e:
             print(f"   ❌ Error: {e}")
             
        # 6. Smart Search
        print("\n[6] Mock Smart Search")
        try:
            resp = await client.post(f"{BASE_URL}/analysis/smart-search", 
                json={"query": "전기 공사", "threshold": 0.5}, 
                headers=headers
            )
            if resp.status_code == 200:
                 results = resp.json().get("results", [])
                 print(f"   ✅ Smart Search Success: {len(results)} matches")
            else:
                 print(f"   ❌ Smart Search Failed: {resp.text}")
        except Exception as e:
             print(f"   ❌ Error: {e}")

    print("\n🏁 Full Cycle Verification Completed.")

if __name__ == "__main__":
    asyncio.run(verify_full_cycle())
