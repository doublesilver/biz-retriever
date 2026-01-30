#!/bin/bash
# 복원 테스트 스크립트 - 테스트 DB에 최신 백업 복원

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"
TEST_CONTAINER="biz-retriever-test-db"
TEST_DB="biz_retriever_test"

# .env 파일 로드
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -E "POSTGRES_USER|POSTGRES_PASSWORD|SLACK_WEBHOOK_URL" | xargs)
fi

# Slack 알림 함수 로드
source "$SCRIPT_DIR/slack-notify.sh"

# PostgreSQL 자격증명 기본값
POSTGRES_USER=${POSTGRES_USER:-admin}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-}

echo "🔄 복원 테스트 시작..."

# Docker Compose 파일 결정
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.pi.yml"
fi

# 1. 최신 백업 파일 찾기
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ 백업 디렉토리를 찾을 수 없습니다: $BACKUP_DIR"
    send_slack_notification "Restore Test Failed" "error" "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 백업 파일을 찾을 수 없습니다"
    send_slack_notification "Restore Test Failed" "error" "No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "📦 최신 백업 파일: $LATEST_BACKUP"

# 2. 기존 테스트 컨테이너 정리
echo "🧹 기존 테스트 컨테이너 정리..."
docker rm -f "$TEST_CONTAINER" 2>/dev/null || true
sleep 2

# 3. 테스트 PostgreSQL 컨테이너 생성
echo "🚀 테스트 PostgreSQL 컨테이너 생성..."
docker run -d \
    --name "$TEST_CONTAINER" \
    -e POSTGRES_DB="$TEST_DB" \
    -e POSTGRES_USER="$POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e POSTGRES_INITDB_ARGS="-E UTF8 --locale=C" \
    postgres:15-alpine \
    > /dev/null

# 컨테이너가 준비될 때까지 대기
echo "⏳ 컨테이너 준비 대기 중..."
for i in {1..30}; do
    if docker exec "$TEST_CONTAINER" pg_isready -U "$POSTGRES_USER" > /dev/null 2>&1; then
        echo "✅ 컨테이너 준비 완료"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 컨테이너 준비 시간 초과"
        docker rm -f "$TEST_CONTAINER" 2>/dev/null || true
        send_slack_notification "Restore Test Failed" "error" "Container startup timeout"
        exit 1
    fi
    sleep 1
done

# 4. 백업 파일 복원
echo "📥 백업 파일 복원 중..."
RESTORE_OUTPUT=$(gunzip -c "$LATEST_BACKUP" | docker exec -i "$TEST_CONTAINER" psql -U "$POSTGRES_USER" -d "$TEST_DB" 2>&1)
RESTORE_EXIT_CODE=$?

if [ $RESTORE_EXIT_CODE -ne 0 ]; then
    echo "❌ 복원 실패"
    echo "오류 메시지: $RESTORE_OUTPUT"
    docker rm -f "$TEST_CONTAINER" 2>/dev/null || true
    send_slack_notification "Restore Test Failed" "error" "Failed to restore backup from $LATEST_BACKUP\nError: $RESTORE_OUTPUT"
    exit 1
fi
echo "✅ 복원 완료"

# 5. 복원된 데이터 검증
echo "🔍 복원된 데이터 검증..."

# 테이블 수 확인
TABLE_COUNT=$(docker exec "$TEST_CONTAINER" psql -U "$POSTGRES_USER" -d "$TEST_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq 0 ]; then
    echo "❌ 테이블을 찾을 수 없습니다"
    docker rm -f "$TEST_CONTAINER" 2>/dev/null || true
    send_slack_notification "Restore Test Failed" "error" "No tables found in restored database"
    exit 1
fi
echo "✅ 테이블 수: $TABLE_COUNT"

# 레코드 수 확인
RECORD_COUNT=$(docker exec "$TEST_CONTAINER" psql -U "$POSTGRES_USER" -d "$TEST_DB" -t -c \
    "SELECT SUM(n_live_tup) FROM pg_stat_user_tables;" 2>/dev/null | tr -d ' ')

if [ -z "$RECORD_COUNT" ] || [ "$RECORD_COUNT" = "NULL" ]; then
    RECORD_COUNT=0
fi
echo "✅ 레코드 수: $RECORD_COUNT"

# 주요 테이블 확인
echo "📋 주요 테이블 확인..."
MAIN_TABLES=$(docker exec "$TEST_CONTAINER" psql -U "$POSTGRES_USER" -d "$TEST_DB" -t -c \
    "SELECT string_agg(tablename, ', ') FROM pg_tables WHERE schemaname='public' LIMIT 5;" 2>/dev/null)
echo "   테이블: $MAIN_TABLES"

# 6. 테스트 컨테이너 정리
echo "🧹 테스트 컨테이너 정리..."
docker rm -f "$TEST_CONTAINER" 2>/dev/null || true

# 완료
echo ""
echo "✅ 복원 테스트 완료!"
echo "   백업 파일: $LATEST_BACKUP"
echo "   테이블 수: $TABLE_COUNT"
echo "   레코드 수: $RECORD_COUNT"

send_slack_notification "Restore Test Passed" "success" "Backup: $(basename $LATEST_BACKUP)\nTables: $TABLE_COUNT\nRecords: $RECORD_COUNT"

exit 0
