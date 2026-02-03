#!/bin/bash

# Vercel 환경 변수 자동 설정 스크립트
# 생성 일시: 2026-02-03

set -e

echo "🚀 Vercel 환경 변수 설정 시작..."
echo ""

# 1. Neon Postgres
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Neon Postgres 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
NEON_URL="postgresql://neondb_owner:npg_KWi4aONZ3dUY@ep-red-math-ahf683ld-pooler.c-3.us-east-1.aws.neon.tech/neondb"

echo "$NEON_URL" | vercel env add NEON_DATABASE_URL production --sensitive
echo "$NEON_URL" | vercel env add NEON_DATABASE_URL preview --sensitive
echo "$NEON_URL" | vercel env add NEON_DATABASE_URL development --sensitive
echo "✅ NEON_DATABASE_URL 설정 완료"
echo ""

# 2. Upstash Redis
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Upstash Redis 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REDIS_URL="rediss://default:AfYuAAIncDEzNzVmMmQ3MDUxMGM0ZWEzOWJjNTQzNWI1NzJjYjdkYnAxNjMwMjI@clear-foxhound-63022.upstash.io:6379"

echo "$REDIS_URL" | vercel env add UPSTASH_REDIS_URL production --sensitive
echo "$REDIS_URL" | vercel env add UPSTASH_REDIS_URL preview --sensitive
echo "$REDIS_URL" | vercel env add UPSTASH_REDIS_URL development --sensitive
echo "✅ UPSTASH_REDIS_URL 설정 완료"
echo ""

# 3. JWT Secret Key
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  JWT Secret Key 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
JWT_SECRET="d8ada904b79bb4113f2e9978c9e0781890d511e004c389a21136c2393e7802f9"

echo "$JWT_SECRET" | vercel env add SECRET_KEY production --sensitive
echo "$JWT_SECRET" | vercel env add SECRET_KEY preview --sensitive
echo "$JWT_SECRET" | vercel env add SECRET_KEY development --sensitive
echo "✅ SECRET_KEY 설정 완료"
echo ""

# 4. Cron Secret
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  Cron Secret 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
CRON_SECRET="a09c601e87b5ad9878f252ce5139be31dcbadaa1b41f47ecd08198ed01451abd"

echo "$CRON_SECRET" | vercel env add CRON_SECRET production --sensitive
echo "$CRON_SECRET" | vercel env add CRON_SECRET preview --sensitive
echo "$CRON_SECRET" | vercel env add CRON_SECRET development --sensitive
echo "✅ CRON_SECRET 설정 완료"
echo ""

# 완료
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 모든 필수 환경 변수 설정 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "설정된 환경 변수:"
echo "  ✅ NEON_DATABASE_URL (production, preview, development)"
echo "  ✅ UPSTASH_REDIS_URL (production, preview, development)"
echo "  ✅ SECRET_KEY (production, preview, development)"
echo "  ✅ CRON_SECRET (production, preview, development)"
echo ""
echo "다음 단계:"
echo "  1. vercel env ls로 확인"
echo "  2. ./scripts/deploy-preview.sh 실행"
echo ""
