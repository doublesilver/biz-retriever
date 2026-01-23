"""
G2B API 키 디버깅 스크립트
다양한 인코딩 방식으로 API 키 테스트
"""
import os
import sys
from pathlib import Path
import urllib.parse

# 프로젝트 루트를 PYTHONPATH에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import httpx
from dotenv import load_dotenv

# .env 로드
load_dotenv()

def test_with_different_encodings():
    """다양한 인코딩으로 API 키 테스트"""
    api_key = os.getenv("G2B_API_KEY")
    endpoint = os.getenv("G2B_API_ENDPOINT")
    
    print("=" * 70)
    print("🔍 G2B API 키 인코딩 테스트")
    print("=" * 70)
    print(f"원본 키: {api_key[:20]}...")
    print(f"엔드포인트: {endpoint}")
    print()
    
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)  # 1일만 조회
    
    # 테스트할 인코딩 방법들
    encodings = [
        ("원본 (Decoding)", api_key),
        ("URL 인코딩 (Encoding)", urllib.parse.quote(api_key)),
        ("URL 인코딩 (safe)", urllib.parse.quote_plus(api_key)),
    ]
    
    for encoding_name, encoded_key in encodings:
        print(f"\n📝 {encoding_name} 테스트")
        print(f"   키: {encoded_key[:30]}...")
        
        params = {
            "ServiceKey": encoded_key,  # 대문자 S
            "numOfRows": "1",
            "pageNo": "1",
            "type": "json",
            "inqryBgnDt": start_date.strftime("%Y%m%d0000"),
            "inqryEndDt": end_date.strftime("%Y%m%d2359")
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, params=params)
            
            print(f"   📥 응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "response" in data:
                        result_code = data["response"]["header"].get("resultCode")
                        result_msg = data["response"]["header"].get("resultMsg")
                        print(f"   📊 결과: {result_code} - {result_msg}")
                        
                        if result_code == "00":
                            print(f"   ✅ 성공! 이 인코딩 방식을 사용하세요: {encoding_name}")
                            return True, encoding_name, encoded_key
                    else:
                        print(f"   📄 응답 본문: {response.text[:100]}")
                except Exception as e:
                    print(f"   📄 응답 본문 (JSON 아님): {response.text[:100]}")
            else:
                print(f"   ❌ HTTP 오류: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
    
    print("\n" + "=" * 70)
    print("❌ 모든 인코딩 방식 실패")
    print()
    print("🔧 확인사항:")
    print("1. 공공데이터포털에서 'Decoding' 키를 사용했는지 확인")
    print("2. 활용 신청이 '승인' 상태인지 확인")
    print("3. API 문서에서 정확한 파라미터명 확인")
    print("   - ServiceKey vs serviceKey")
    print("   - 필수 파라미터 누락 여부")
    return False, None, None


if __name__ == "__main__":
    success, method, key = test_with_different_encodings()
    sys.exit(0 if success else 1)
