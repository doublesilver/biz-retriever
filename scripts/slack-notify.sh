#!/bin/bash
# Slack 알림 헬퍼 함수

# 사용법: send_slack_notification "메시지" "상태" "상세정보"
# 상태: success, error, warning, info

send_slack_notification() {
    local message=$1
    local status=${2:-info}
    local details=${3:-""}
    
    # Slack webhook URL 확인
    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        echo "⚠️  SLACK_WEBHOOK_URL not set, skipping notification"
        return 0
    fi
    
    # 상태에 따른 색상 설정
    local color
    case $status in
        success)
            color="#36a64f"
            emoji="✅"
            ;;
        error)
            color="#ff0000"
            emoji="❌"
            ;;
        warning)
            color="#ffaa00"
            emoji="⚠️"
            ;;
        *)
            color="#0099ff"
            emoji="ℹ️"
            ;;
    esac
    
    # JSON 페이로드 생성
    local payload=$(cat <<PAYLOAD
{
    "attachments": [
        {
            "color": "$color",
            "title": "$emoji $message",
            "text": "$details",
            "footer": "Database Backup System",
            "ts": $(date +%s)
        }
    ]
}
PAYLOAD
)
    
    # Slack에 전송
    curl -X POST \
        -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" \
        2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "📤 Slack notification sent"
    else
        echo "⚠️  Failed to send Slack notification"
    fi
}

# 직접 실행 시 테스트
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    # .env 파일 로드
    if [ -f "../.env" ]; then
        export $(cat "../.env" | grep SLACK_WEBHOOK_URL | xargs)
    fi
    
    send_slack_notification "Test Notification" "info" "This is a test message from backup system"
fi
