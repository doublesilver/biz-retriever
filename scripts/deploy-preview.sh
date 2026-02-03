#!/bin/bash

# Vercel Preview 배포 자동화 스크립트
# Usage: ./scripts/deploy-preview.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Vercel Preview 배포 시작...${NC}"
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo -e "${RED}❌ Error: Vercel CLI가 설치되지 않았습니다.${NC}"
    echo ""
    echo "설치 방법:"
    echo -e "  ${BLUE}npm install -g vercel${NC}"
    echo ""
    exit 1
fi

# Check if logged in
echo -e "${YELLOW}🔍 Vercel 로그인 상태 확인...${NC}"
if ! vercel whoami &> /dev/null; then
    echo -e "${YELLOW}⚠️  Vercel에 로그인되어 있지 않습니다.${NC}"
    echo ""
    echo -e "${BLUE}로그인을 시작합니다...${NC}"
    vercel login
fi

VERCEL_USER=$(vercel whoami)
echo -e "${GREEN}✅ 로그인됨: ${VERCEL_USER}${NC}"
echo ""

# Check if project is linked
echo -e "${YELLOW}🔍 프로젝트 연결 상태 확인...${NC}"
if [ ! -f ".vercel/project.json" ]; then
    echo -e "${YELLOW}⚠️  프로젝트가 연결되어 있지 않습니다.${NC}"
    echo ""
    echo -e "${BLUE}프로젝트 연결을 시작합니다...${NC}"
    vercel link
    echo ""
fi

PROJECT_ID=$(cat .vercel/project.json | grep -o '"projectId": "[^"]*' | cut -d'"' -f4)
echo -e "${GREEN}✅ 프로젝트 연결됨: ${PROJECT_ID}${NC}"
echo ""

# Check environment variables
echo -e "${YELLOW}🔍 환경 변수 확인...${NC}"
echo ""

REQUIRED_VARS=("NEON_DATABASE_URL" "UPSTASH_REDIS_URL" "SECRET_KEY" "CRON_SECRET")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    echo -n "  ${var}... "
    if vercel env ls 2>/dev/null | grep -q "$var"; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌ MISSING${NC}"
        MISSING_VARS+=("$var")
    fi
done

echo ""

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ 필수 환경 변수가 누락되었습니다:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  - ${var}"
    done
    echo ""
    echo -e "${YELLOW}설정 방법:${NC}"
    echo -e "  ${BLUE}./setup-vercel-env.md${NC} 가이드를 참고하세요."
    echo ""
    echo "계속 진행하시겠습니까? (일부 기능이 동작하지 않을 수 있습니다)"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}현재 브랜치: ${CURRENT_BRANCH}${NC}"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Warning: 커밋되지 않은 변경사항이 있습니다.${NC}"
    echo ""
    git status --short
    echo ""
    echo "커밋하지 않고 계속하시겠습니까?"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}커밋 후 다시 실행하세요:${NC}"
        echo -e "  ${BLUE}git add .${NC}"
        echo -e "  ${BLUE}git commit -m 'your message'${NC}"
        echo -e "  ${BLUE}./scripts/deploy-preview.sh${NC}"
        echo ""
        exit 1
    fi
fi

# Deploy to preview
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🚀 Preview 배포 시작${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Deploy
DEPLOYMENT_OUTPUT=$(vercel --yes 2>&1)
DEPLOYMENT_URL=$(echo "$DEPLOYMENT_OUTPUT" | grep -o 'https://[^ ]*\.vercel\.app' | head -1)

if [ -z "$DEPLOYMENT_URL" ]; then
    echo -e "${RED}❌ 배포 실패${NC}"
    echo ""
    echo "$DEPLOYMENT_OUTPUT"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 배포 성공!${NC}"
echo ""
echo -e "${BLUE}Preview URL: ${DEPLOYMENT_URL}${NC}"
echo ""

# Wait for deployment to be ready
echo -e "${YELLOW}⏳ 배포 준비 대기 중...${NC}"
sleep 10

# Run verification
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 배포 검증 시작${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "./scripts/verify-deployment.sh" ]; then
    chmod +x ./scripts/verify-deployment.sh
    ./scripts/verify-deployment.sh "$DEPLOYMENT_URL"
else
    echo -e "${YELLOW}⚠️  verify-deployment.sh 스크립트를 찾을 수 없습니다.${NC}"
    echo ""
    echo -e "${BLUE}수동으로 확인하세요:${NC}"
    echo -e "  Health: ${DEPLOYMENT_URL}/health"
    echo -e "  Docs:   ${DEPLOYMENT_URL}/docs"
    echo -e "  App:    ${DEPLOYMENT_URL}/"
fi

echo ""
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo -e "  1. 브라우저에서 테스트: ${DEPLOYMENT_URL}"
echo -e "  2. Vercel 대시보드 확인: https://vercel.com/dashboard"
echo -e "  3. 로그 확인: ${BLUE}vercel logs --follow${NC}"
echo -e "  4. 문제 없으면 main에 병합 후 프로덕션 배포"
echo ""
