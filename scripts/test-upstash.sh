#!/bin/bash

# Upstash Redis 연결 테스트 스크립트
# Usage: ./scripts/test-upstash.sh <UPSTASH_REDIS_URL>

set -e

echo "🚀 Upstash Redis 연결 테스트..."
echo ""

# Check if REDIS_URL is provided
if [ -z "$1" ]; then
    echo "❌ Error: Upstash REDIS_URL이 필요합니다."
    echo ""
    echo "사용법: ./scripts/test-upstash.sh <UPSTASH_REDIS_URL>"
    echo ""
    echo "예시:"
    echo "  ./scripts/test-upstash.sh 'redis://default:password@us1-xxx-xxx.upstash.io:6379'"
    echo ""
    exit 1
fi

export REDIS_URL="$1"

echo "✅ Redis URL 설정 완료"
echo ""

# Test connection
echo "🔍 연결 테스트 중..."
python -c "
import asyncio
import redis.asyncio as redis

async def test_redis():
    client = redis.from_url('$REDIS_URL', encoding='utf-8', decode_responses=True)
    try:
        # PING 테스트
        pong = await client.ping()
        print(f'✅ PING 테스트 성공: {pong}')
        
        # SET/GET 테스트
        await client.set('test:key', 'Hello from Upstash!')
        value = await client.get('test:key')
        print(f'✅ SET/GET 테스트 성공: {value}')
        
        # INFO 테스트
        info = await client.info('server')
        print(f'✅ Redis 버전: {info.get(\"redis_version\", \"N/A\")}')
        
        # Cleanup
        await client.delete('test:key')
        print('✅ 테스트 키 정리 완료')
        
    except Exception as e:
        print(f'❌ 연결 실패: {e}')
        raise
    finally:
        await client.close()

asyncio.run(test_redis())
" || {
    echo "❌ Redis 연결 실패!"
    echo "   연결 문자열을 확인하세요."
    exit 1
}

echo ""
echo "🎉 Upstash Redis 연결 성공!"
echo ""
echo "다음 단계:"
echo "  1. Vercel 환경 변수에 UPSTASH_REDIS_URL 설정"
echo "  2. 캐시 기능 테스트"
echo "  3. Rate limiting 동작 확인"
echo ""
