#!/bin/bash

# Neon Postgres 마이그레이션 스크립트
# Usage: ./scripts/migrate-to-neon.sh <NEON_DATABASE_URL>

set -e

echo "🚀 Neon Postgres 마이그레이션 시작..."
echo ""

# Check if DATABASE_URL is provided
if [ -z "$1" ]; then
    echo "❌ Error: Neon DATABASE_URL이 필요합니다."
    echo ""
    echo "사용법: ./scripts/migrate-to-neon.sh <NEON_DATABASE_URL>"
    echo ""
    echo "예시:"
    echo "  ./scripts/migrate-to-neon.sh 'postgresql://user:password@ep-xxx-xxx.neon.tech/database?pgbouncer=true'"
    echo ""
    exit 1
fi

export DATABASE_URL="$1"

echo "✅ 데이터베이스 URL 설정 완료"
echo ""

# Test connection
echo "🔍 연결 테스트 중..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    engine = create_async_engine('$DATABASE_URL'.replace('postgresql://', 'postgresql+asyncpg://'))
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT version()'))
        version = result.scalar()
        print(f'✅ 연결 성공! PostgreSQL version: {version[:50]}...')
    await engine.dispose()

asyncio.run(test_connection())
" || {
    echo "❌ 데이터베이스 연결 실패!"
    echo "   연결 문자열을 확인하세요."
    exit 1
}

echo ""
echo "📦 Alembic 마이그레이션 실행 중..."
alembic upgrade head

echo ""
echo "✅ 마이그레이션 완료!"
echo ""
echo "🔍 테이블 확인:"
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def list_tables():
    engine = create_async_engine('$DATABASE_URL'.replace('postgresql://', 'postgresql+asyncpg://'))
    async with engine.connect() as conn:
        result = await conn.execute(text('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        '''))
        tables = result.fetchall()
        print('')
        for table in tables:
            print(f'  - {table[0]}')
        print(f'\n  총 {len(tables)}개 테이블 생성됨')
    await engine.dispose()

asyncio.run(list_tables())
"

echo ""
echo "🎉 Neon 데이터베이스 준비 완료!"
echo ""
echo "다음 단계:"
echo "  1. Vercel 환경 변수에 NEON_DATABASE_URL 설정"
echo "  2. vercel deploy로 Preview 배포 테스트"
echo "  3. Health check API 확인: https://your-url.vercel.app/health"
echo ""
