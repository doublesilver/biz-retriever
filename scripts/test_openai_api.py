"""
OpenAI API 키 테스트 스크립트
AI 분석 기능이 정상 작동하는지 검증
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

# .env 로드
load_dotenv()

def test_openai_api():
    """OpenAI API 키 테스트"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    print("=" * 60)
    print("🤖 OpenAI API 키 테스트")
    print("=" * 60)
    
    # API 키 확인
    if not api_key or api_key == "sk-mock-key-for-verification" or "your" in api_key.lower():
        print("❌ OpenAI API 키가 설정되지 않았습니다!")
        print("\n📋 발급 방법:")
        print("1. https://platform.openai.com/ 접속")
        print("2. 계정 생성 및 로그인")
        print("3. Settings → Billing → 결제 정보 등록")
        print("4. API keys → 'Create new secret key'")
        print("5. 키 복사 (한 번만 표시됨!)")
        print("6. .env 파일에 OPENAI_API_KEY=sk-... 입력")
        print("\n💰 예상 비용:")
        print("- 모델: gpt-4o-mini (권장)")
        print("- 공고 100개/일분석 시: 약 $10~30/월")
        return False
    
    print(f"✅ API 키 확인: {api_key[:20]}...")
    print()
    
    # OpenAI 라이브러리 확인
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ OpenAI 라이브러리가 설치되지 않았습니다.")
        print("설치: pip install openai")
        return False
    
    # API 테스트
    try:
        print("🚀 API 연결 테스트 중...")
        client = OpenAI(api_key=api_key)
        
        # 간단한 테스트 요청
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OK' if you can read this."}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"📥 응답: {result}")
        
        # 사용량 정보
        print(f"\n📊 토큰 사용량:")
        print(f"  - 입력: {response.usage.prompt_tokens} 토큰")
        print(f"  - 출력: {response.usage.completion_tokens} 토큰")
        print(f"  - 총합: {response.usage.total_tokens} 토큰")
        
        # 예상 비용 (gpt-4o-mini 기준)
        input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.15
        output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
        total_cost = input_cost + output_cost
        print(f"\n💵 이번 요청 비용: ${total_cost:.6f}")
        
        print("\n✅ OpenAI API가 정상적으로 작동합니다!")
        print("\n💡 비용 관리 팁:")
        print("1. OpenAI Dashboard → Usage에서 사용량 모니터링")
        print("2. Billing → Usage limits에서 월 한도 설정 권장")
        print("3. 프로덕션 환경에서는 max_tokens를 500 이하로 제한")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ API 오류: {error_msg}")
        
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            print("\n🔧 API 키 오류:")
            print("1. API 키가 정확한지 확인")
            print("2. .env 파일에서 따옴표 제거 확인")
            print("3. OpenAI 계정이 활성화되었는지 확인")
        elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
            print("\n💳 결제 정보 오류:")
            print("1. OpenAI Dashboard → Billing 확인")
            print("2. 결제 수단이 등록되었는지 확인")
            print("3. 크레딧 잔액 확인")
        else:
            print(f"\n🔧 오류 상세: {error_msg}")
        
        return False
    finally:
        print("=" * 60)


if __name__ == "__main__":
    success = test_openai_api()
    sys.exit(0 if success else 1)
