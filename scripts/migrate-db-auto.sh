#!/bin/bash
# DB 마이그레이션 자동화 스크립트 (라즈베리파이 → Vercel)

set -e  # 에러 시 중단

echo "🚀 Biz-Retriever DB Migration Script"
echo "======================================"
echo ""

# 1. 라즈베리파이 DB 백업
echo "📦 Step 1: Backup Raspberry Pi Database"
echo "----------------------------------------"

# SSH 접속 정보
RPI_HOST="${RPI_HOST:-leeeunseok.tail32c3e2.ts.net}"
RPI_USER="${RPI_USER:-pi}"

echo "Connecting to $RPI_USER@$RPI_HOST..."

# Docker container 찾기
CONTAINER_ID=$(ssh $RPI_USER@$RPI_HOST "docker ps --filter 'name=postgres' --format '{{.ID}}' | head -1")

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Error: Postgres container not found on Raspberry Pi"
    exit 1
fi

echo "Found Postgres container: $CONTAINER_ID"

# DB 덤프
echo "Creating database dump..."
ssh $RPI_USER@$RPI_HOST "docker exec $CONTAINER_ID pg_dump -U admin -d biz_retriever -F c -f /tmp/biz_retriever_dump.backup"

# 로컬로 다운로드
echo "Downloading backup to local..."
scp $RPI_USER@$RPI_HOST:/tmp/biz_retriever_dump.backup ./biz_retriever_dump.backup

echo "✅ Backup completed: biz_retriever_dump.backup"
echo ""

# 2. Vercel Postgres로 복원
echo "📤 Step 2: Restore to Vercel Postgres/Neon"
echo "--------------------------------------------"

# Vercel 환경 변수에서 connection string 가져오기
if [ -z "$TARGET_DATABASE_URL" ]; then
    echo "Fetching Vercel environment variables..."
    vercel env pull .env.production
    source .env.production
    TARGET_DATABASE_URL="${POSTGRES_URL:-$DATABASE_URL}"
fi

if [ -z "$TARGET_DATABASE_URL" ]; then
    echo "❌ Error: TARGET_DATABASE_URL not found"
    echo "Please set TARGET_DATABASE_URL environment variable or run 'vercel env pull'"
    exit 1
fi

# Connection string 파싱
echo "Target database: ${TARGET_DATABASE_URL%%@*}@..."

# pg_restore 실행
echo "Restoring database..."
pg_restore --verbose --clean --no-acl --no-owner \
    -d "$TARGET_DATABASE_URL" \
    biz_retriever_dump.backup

echo "✅ Restore completed"
echo ""

# 3. 검증
echo "🔍 Step 3: Verification"
echo "------------------------"

# Python 스크립트로 row count 비교
python3 << 'EOF'
import asyncio
import os
import asyncpg

async def verify():
    target_url = os.getenv("TARGET_DATABASE_URL")
    conn = await asyncpg.connect(target_url)
    
    tables = ["users", "bid_announcements", "profiles"]
    print("\nTable row counts:")
    for table in tables:
        try:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
            print(f"  {table}: {count:,} rows")
        except Exception as e:
            print(f"  {table}: Table not found or error: {e}")
    
    await conn.close()

asyncio.run(verify())
EOF

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Verify data in Vercel dashboard: https://vercel.com/storage"
echo "  2. Test API endpoints: https://your-app.vercel.app/api/health"
echo "  3. Deploy to production: git push origin master"
