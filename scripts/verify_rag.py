import asyncio
import sys
import os

# Create a valid event loop for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.services.rag_service import rag_service

async def main():
    print("Testing RAG Service...")
    
    # Check if API Key is detected
    if not rag_service.api_key_type:
        print("❌ API Key not configured (Unknown Type)")
    else:
        print(f"✅ API Configured: {rag_service.api_key_type}")

    # Test Content
    test_content = """
    [공고] 2026년도 광양시 스마트시티 조성사업 용역 입찰 공고
    1. 사업명: 스마트시티 통합플랫폼 구축
    2. 예산: 500,000,000원
    3. 기간: 착수일로부터 6개월
    4. 주요과업: 
       - CCTV 통합관제센터 연계
       - 시민 안전 서비스 개발
       - 데이터 허브 구축
    5. 참가자격: 소프트웨어사업자(컴퓨터관련서비스사업) 등
    """
    
    print("\n[Input]")
    print(test_content.strip())
    
    print("\n[Analyzing...]")
    result = await rag_service.analyze_bid(test_content)
    
    print("\n[Result]")
    print(f"Summary: {result.get('summary')}")
    print(f"Keywords: {result.get('keywords')}")

if __name__ == "__main__":
    asyncio.run(main())
