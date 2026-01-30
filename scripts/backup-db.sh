#!/bin/bash
# DB 자동 백업 스크립트 (cron 자동화용)

set -e

DATE=$(date +%Y%m%d_%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"
BACKUP_FILE_GZ="$BACKUP_FILE.gz"

# .env 파일 로드
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -E "POSTGRES_USER|POSTGRES_PASSWORD|SLACK_WEBHOOK_URL" | xargs)
fi

# Slack 알림 함수 로드
source "$SCRIPT_DIR/slack-notify.sh"

# PostgreSQL 자격증명 기본값
POSTGRES_USER=${POSTGRES_USER:-admin}

mkdir -p "$BACKUP_DIR"

echo "📦 데이터베이스 백업 중... ($(date '+%Y-%m-%d %H:%M:%S'))"

# 백업 실행 (docker-compose.yml 또는 docker-compose.pi.yml 중 존재하는 것 사용)
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.pi.yml"
fi

# 서비스명 결정 (db 또는 postgres)
SERVICE_NAME="db"
if ! docker-compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME" 2>/dev/null | grep -q "$SERVICE_NAME"; then
    SERVICE_NAME="postgres"
fi

if docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" pg_dump -U "$POSTGRES_USER" biz_retriever > "$BACKUP_FILE" 2>/dev/null; then
    echo "✅ 백업 완료: $BACKUP_FILE"
    
    # 압축
    if gzip "$BACKUP_FILE"; then
        echo "✅ 압축 완료: $BACKUP_FILE_GZ"
        
        # 백업 검증
        echo "🔍 백업 검증 중..."
        if bash "$SCRIPT_DIR/verify-backup.sh" "$BACKUP_FILE_GZ" > /dev/null 2>&1; then
            echo "✅ 백업 검증 통과"
            
            # 14일 이상 된 백업 파일 삭제
            echo "🧹 오래된 백업 파일 정리 중..."
            DELETED_COUNT=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete -print | wc -l)
            if [ "$DELETED_COUNT" -gt 0 ]; then
                echo "🧹 $DELETED_COUNT개의 오래된 백업 파일 삭제"
            fi
            
            # 성공 알림
            BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE_GZ" 2>/dev/null || stat -c%s "$BACKUP_FILE_GZ" 2>/dev/null)
            send_slack_notification "Database Backup Successful" "success" "File: $(basename $BACKUP_FILE_GZ)\nSize: ${BACKUP_SIZE} bytes\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
            
            echo "✅ 백업 프로세스 완료"
            exit 0
        else
            echo "❌ 백업 검증 실패"
            send_slack_notification "Database Backup Verification Failed" "error" "Backup file: $(basename $BACKUP_FILE_GZ)\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
            exit 1
        fi
    else
        echo "❌ 압축 실패"
        send_slack_notification "Database Backup Compression Failed" "error" "Failed to compress backup file\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
        exit 1
    fi
else
    echo "❌ 백업 실패"
    send_slack_notification "Database Backup Failed" "error" "Failed to create database backup\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
    exit 1
fi
