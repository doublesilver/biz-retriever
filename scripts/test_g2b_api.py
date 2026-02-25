"""
G2B API 최종 테스트 - 공공데이터개방표준서비스
참고문서: 조달청_OpenAPI참고자료_나라장터_공공데이터개방표준서비스_1.1.docx
"""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import httpx
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def test_g2b_open_standard():
    """공공데이터개방표준서비스 테스트"""
    api_key = os.getenv("G2B_API_KEY")
    
    print("=" * 70)
    print("🔍 G2B 공공데이터개방표준서비스 테스트")
    print("=" * 70)
    print(f"API 키: {api_key[:20]}...")
    print()
    
    # 엔드포인트
    base_url = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
    endpoint = f"{base_url}/getDataSetOpnStdBidPblancInfo"
    
    # 날짜 설정 (최근 1일)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    # 테스트할 파라미터 조합
    param_variations = [
        {
            "name": "기본 파라미터 (소문자 serviceKey)",
            "params": {
                "serviceKey": api_key,
                "numOfRows": "10",
                "pageNo": "1",
                "type": "json",
                "inqryBgnDt": start_date.strftime("%Y%m%d%H%M"),
                "inqryEndDt": end_date.strftime("%Y%m%d%H%M")
            }
        },
        {
            "name": "대문자 ServiceKey",
            "params": {
                "ServiceKey": api_key,
                "numOfRows": "10",
                "pageNo": "1",
                "type": "json",
                "inqryBgnDt": start_date.strftime("%Y%m%d%H%M"),
                "inqryEndDt": end_date.strftime("%Y%m%d%H%M")
            }
        },
        {
            "name": "날짜 형식 변경 (YYYYMMDD)",
            "params": {
                "serviceKey": api_key,
                "numOfRows": "10",
                "pageNo": "1",
                "type": "json",
                "inqryBgnDt": start_date.strftime("%Y%m%d"),
                "inqryEndDt": end_date.strftime("%Y%m%d")
            }
        },
        {
            "name": "최소 파라미터",
            "params": {
                "serviceKey": api_key,
                "type": "json"
            }
        }
    ]
    
    for variation in param_variations:
        print(f"\n📝 테스트: {variation['name']}")
        print(f"   파라미터: {list(variation['params'].keys())}")
        
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(endpoint, params=variation['params'])
            
            print(f"   📥 응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   📊 JSON 파싱: 성공")
                    
                    # 응답 구조 출력
                    if "response" in data:
                        header = data["response"].get("header", {})
                        result_code = header.get("resultCode")
                        result_msg = header.get("resultMsg")
                        
                        print(f"   📋 결과 코드: {result_code}")
                        print(f"   💬 결과 메시지: {result_msg}")
                        
                        if result_code == "00":
                            print(f"   ✅ 성공!")
                            
                            body = data["response"].get("body", {})
                            total_count = body.get("totalCount", 0)
                            print(f"   💾 전체 건수: {total_count}")
                            
                            items = body.get("items", [])
                            if items:
                                print(f"   📄 샘플 데이터:")
                                sample = items[0] if isinstance(items, list) else items
                                for key, value in list(sample.items())[:5]:
                                    print(f"      - {key}: {value}")
                            
                            return True
                        else:
                            print(f"   ❌ API 오류: {result_msg}")
                    else:
                        # response 키가 없는 경우
                        print(f"   📄 응답 구조:")
                        for key in list(data.keys())[:10]:
                            print(f"      - {key}: {type(data[key])}")
                        
                except Exception as e:
                    print(f"   ❌ JSON 파싱 실패: {e}")
                    print(f"   📄 응답 본문 (처음 200자): {response.text[:200]}")
            else:
                print(f"   ❌ HTTP 오류")
                print(f"   📄 응답: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ 요청 실패: {e}")
    
    print("\n" + "=" * 70)
    print("❌ 모든 테스트 실패")
    print()
    print("🔧 추가 확인사항:")
    print("1. API 문서에서 필수 파라미터 확인")
    print("2. 날짜 형식 확인 (YYYYMMDDhhmm vs YYYYMMDD)")
    print("3. 공공데이터포털에서 'API 신청 현황' 재확인")
    print("4. 서비스 계정 상태 확인 (정지/제한 여부)")
    return False


if __name__ == "__main__":
    success = test_g2b_open_standard()
    sys.exit(0 if success else 1)
