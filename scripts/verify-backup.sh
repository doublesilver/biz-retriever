#!/bin/bash
# 백업 파일 무결성 검증 스크립트

set -e

BACKUP_FILE=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# .env 파일 로드
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep SLACK_WEBHOOK_URL | xargs)
fi

# Slack 알림 함수 로드
if [ -f "$SCRIPT_DIR/slack-notify.sh" ]; then
    source "$SCRIPT_DIR/slack-notify.sh"
else
    # Slack 알림 함수가 없으면 더미 함수 정의
    send_slack_notification() { :; }
fi

# 사용법 확인
if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 사용법: $0 <backup_file>"
    echo "예: $0 data/backups/db_backup_20240130_030000.sql.gz"
    exit 1
fi

# 파일 존재 확인
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ 백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
    send_slack_notification "Backup Verification Failed" "error" "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔍 백업 파일 검증 시작: $BACKUP_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. 파일 크기 확인 (최소 1KB)
echo "1️⃣  파일 크기 검증 중..."
FILE_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
MIN_SIZE=$((1024))  # 1KB

if [ "$FILE_SIZE" -lt "$MIN_SIZE" ]; then
    echo "   ❌ 파일 크기 검증 실패: ${FILE_SIZE} bytes (최소: ${MIN_SIZE} bytes)"
    send_slack_notification "Backup Verification Failed" "error" "File size too small: ${FILE_SIZE} bytes (minimum: ${MIN_SIZE} bytes)"
    exit 1
fi

# 파일 크기를 적절한 단위로 표시
if [ "$FILE_SIZE" -ge $((1024 * 1024)) ]; then
    SIZE_DISPLAY="$((FILE_SIZE / 1024 / 1024))MB"
elif [ "$FILE_SIZE" -ge 1024 ]; then
    SIZE_DISPLAY="$((FILE_SIZE / 1024))KB"
else
    SIZE_DISPLAY="${FILE_SIZE}B"
fi
echo "   ✅ 파일 크기 검증 통과 (${SIZE_DISPLAY})"

# 2. gzip 무결성 검증
echo "2️⃣  gzip 무결성 검증 중..."
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "   ❌ gzip 무결성 검증 실패"
    send_slack_notification "Backup Verification Failed" "error" "gzip integrity check failed for $BACKUP_FILE"
    exit 1
fi
echo "   ✅ gzip 무결성 검증 통과"

# 3. PostgreSQL 헤더 검증
echo "3️⃣  PostgreSQL 헤더 검증 중..."
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

if ! gunzip -c "$BACKUP_FILE" 2>/dev/null | head -c 100 > "$TEMP_FILE"; then
    echo "   ❌ 백업 파일 압축 해제 실패"
    send_slack_notification "Backup Verification Failed" "error" "Failed to decompress backup file"
    exit 1
fi

# PostgreSQL dump 파일의 특징적인 헤더 확인
if ! grep -q "PostgreSQL database dump" "$TEMP_FILE" 2>/dev/null; then
    echo "   ⚠️  PostgreSQL 헤더를 찾을 수 없습니다 (경고)"
else
    echo "   ✅ PostgreSQL 헤더 검증 통과"
fi

# 4. 백업 파일에서 테이블 수 확인
echo "4️⃣  테이블 검증 중..."
TABLE_COUNT=$(gunzip -c "$BACKUP_FILE" 2>/dev/null | grep -c "^CREATE TABLE" || echo "0")
if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "   ⚠️  테이블을 찾을 수 없습니다 (경고)"
else
    echo "   ✅ 테이블 검증 통과: $TABLE_COUNT 개 테이블 발견"
fi

# 모든 검증 통과
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 백업 검증 완료!"
echo "   파일: $BACKUP_FILE"
echo "   크기: ${SIZE_DISPLAY} (${FILE_SIZE} bytes)"
echo "   테이블: $TABLE_COUNT"

send_slack_notification "Backup Verification Passed" "success" "File: $BACKUP_FILE\nSize: ${FILE_SIZE} bytes\nTables: $TABLE_COUNT"

exit 0
