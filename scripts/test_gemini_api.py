"""
Google Gemini API 테스트 스크립트 (Rate Limit 대응)
"""
import os
import sys
from pathlib import Path
import time

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()

def test_gemini_api():
    """Gemini API 키 테스트 (Rate Limit 대응)"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("=" * 70)
    print("🤖 Google Gemini API 테스트")
    print("=" * 70)
    
    if not api_key or not api_key.startswith("AIza"):
        print("❌ Gemini API 키가 설정되지 않았습니다!")
        print("\n📋 발급 방법:")
        print("1. https://makersuite.google.com/app/apikey 접속")
        print("2. 'Create API key' 클릭")
        print("3. .env 파일에 GEMINI_API_KEY=<키> 입력")
        return False
    
    print(f"✅ API 키 확인: {api_key[:20]}...")
    print()
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        # 모델 목록 확인
        print("📋 사용 가능한 모델 확인 중...")
        try:
            models = client.models.list()
            available_models = [m.name for m in models if 'gemini' in m.name.lower()]
            print(f"   사용 가능한 Gemini 모델: {len(available_models)}개")
            for model in available_models[:5]:
                print(f"   - {model}")
        except Exception as e:
            print(f"   ⚠️ 모델 목록 조회 실패: {e}")
        
        print()
        
        # 테스트 모델 목록
        test_models = [
            'gemini-2.5-flash',
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash',
            'gemini-1.5-pro'
        ]
        
        success = False
        for model_name in test_models:
            print(f"🚀 {model_name} 테스트 중...")
            
            try:
                # Rate Limit 방지를 위해 짧은 대기
                time.sleep(2)
                
                response = client.models.generate_content(
                    model=model_name,
                    contents="안녕하세요! 간단히 '테스트 성공'이라고만 답변해주세요."
                )
                
                print(f"   📥 응답: {response.text}")
                print(f"   ✅ {model_name} 정상 작동!")
                success = True
                
                print(f"\n💡 사용할 모델: {model_name}")
                break
                
            except Exception as e:
                error_msg = str(e)
                if '404' in error_msg or 'not found' in error_msg.lower():
                    print(f"   ❌ 404: {model_name} 모델을 찾을 수 없음")
                elif '429' in error_msg or 'quota' in error_msg.lower():
                    print(f"   ⏳ 429: Rate Limit 초과, 다음 모델 시도...")
                    time.sleep(5)  # 더 긴 대기
                else:
                    print(f"   ❌ 오류: {error_msg[:100]}")
        
        if success:
            print("\n💰 Gemini API 비용:")
            print("  - 무료 할당량: 매일 1,500 requests (15 RPM)")
            print("  - Flash 모델: 매우 빠르고 효율적")
            
            print("\n📊 프로젝트 예상 사용량:")
            print("  - 공고 분석 100건/일 = ~100 requests")
            print("  - 무료 할당량으로 충분!")
            return True
        else:
            print("\n❌ 모든 모델 테스트 실패")
            print("\n🔧 추가 확인사항:")
            print("1. Google AI Studio에서 API 활성화 확인")
            print("2. 프로젝트가 올바르게 설정되었는지 확인")
            print("3. 몇 분 후 재시도 (Rate Limit 리셋)")
            return False
        
    except ImportError:
        print("❌ google-genai 패키지가 설치되지 않았습니다.")
        print("설치: pip install google-genai")
        return False
    except Exception as e:
        print(f"❌ Gemini API 오류: {e}")
        return False
    finally:
        print("=" * 70)


if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)
