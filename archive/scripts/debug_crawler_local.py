import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.core.logging")
logger.setLevel(logging.DEBUG)

from dotenv import load_dotenv
load_dotenv()

async def debug_crawler():
    print("=== G2B Crawler Local Debugging ===")
    
    try:
        from app.services.crawler_service import g2b_crawler
        print("[OK] Service Imported")
        
        print("\n1. Calling fetch_new_announcements()...")
        print("(DB connection might fail if not running locally, but API call should proceed)")
        
        # Call the actual service method
        results = await g2b_crawler.fetch_new_announcements()
        
        print(f"\n[RESULT] Fetched {len(results)} items.")
        
        if results:
            print("\n--- Sample Item ---")
            print(results[0])
            print("-------------------")
        else:
            print("\n[WARNING] No items fetched. Check logs above for API errors or filtering issues.")

    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        print("Make sure run this from project root or scripts folder.")
    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_crawler())
