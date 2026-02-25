"""
Slack Webhook 테스트 스크립트
알림이 정상적으로 전송되는지 검증
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import httpx
from dotenv import load_dotenv

# .env 로드
load_dotenv()

def test_slack_webhook():
    """Slack Webhook 테스트"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    channel = os.getenv("SLACK_CHANNEL", "#입찰-알림")
    
    print("=" * 60)
    print("📢 Slack Webhook 테스트")
    print("=" * 60)
    
    # Webhook URL 확인
    if not webhook_url or "YOUR/WEBHOOK/URL" in webhook_url:
        print("❌ Slack Webhook URL이 설정되지 않았습니다!")
        print("\n📋 설정 방법:")
        print("1. Slack Workspace 접속")
        print("2. Apps → 'Incoming Webhooks' 검색")
        print("3. 'Add to Slack' 클릭")
        print("4. 채널 선택 (예: #입찰-알림)")
        print("5. Webhook URL 복사")
        print("6. .env 파일에 SLACK_WEBHOOK_URL=<URL> 입력")
        return False
    
    print(f"✅ Webhook URL 확인: {webhook_url[:30]}...")
    print(f"📺 채널: {channel}")
    print()
    
    # 테스트 메시지 전송
    test_message = {
        "channel": channel,
        "username": "Biz-Retriever Bot",
        "icon_emoji": ":robot_face:",
        "text": "🎉 *Slack 알림 테스트 성공!*",
        "attachments": [
            {
                "color": "#36a64f",
                "title": "테스트 공고",
                "text": "Biz-Retriever가 정상적으로 작동 중입니다.",
                "fields": [
                    {
                        "title": "상태",
                        "value": "✅ 정상",
                        "short": True
                    },
                    {
                        "title": "시간",
                        "value": "2026-01-23 08:30",
                        "short": True
                    }
                ],
                "footer": "Biz-Retriever",
                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
            }
        ]
    }
    
    try:
        print("🚀 테스트 메시지 전송 중...")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook_url, json=test_message)
        
        print(f"📥 응답 코드: {response.status_code}")
        
        if response.status_code == 200 and response.text == "ok":
            print("\n✅ Slack 알림이 성공적으로 전송되었습니다!")
            print(f"📺 {channel} 채널을 확인하세요.")
            return True
        else:
            print(f"❌ 전송 실패: {response.text}")
            print("\n🔧 확인 사항:")
            print("1. Webhook URL이 정확한지 확인")
            print("2. 채널이 존재하는지 확인")
            print("3. Webhook이 삭제되지 않았는지 확인")
            return False
            
    except httpx.TimeoutException:
        print("❌ 요청 시간 초과 (10초)")
        print("네트워크 연결을 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False
    finally:
        print("=" * 60)


if __name__ == "__main__":
    success = test_slack_webhook()
    sys.exit(0 if success else 1)
