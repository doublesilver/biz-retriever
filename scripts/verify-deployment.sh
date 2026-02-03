#!/bin/bash

# Vercel 배포 검증 스크립트
# Usage: ./scripts/verify-deployment.sh <DEPLOYMENT_URL>

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if URL is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Deployment URL이 필요합니다.${NC}"
    echo ""
    echo "사용법: ./scripts/verify-deployment.sh <DEPLOYMENT_URL>"
    echo ""
    echo "예시:"
    echo "  ./scripts/verify-deployment.sh https://biz-retriever-xxx.vercel.app"
    echo ""
    exit 1
fi

DEPLOYMENT_URL="$1"
# Remove trailing slash
DEPLOYMENT_URL="${DEPLOYMENT_URL%/}"

echo -e "${BLUE}🚀 Vercel 배포 검증 시작...${NC}"
echo -e "${BLUE}📍 URL: ${DEPLOYMENT_URL}${NC}"
echo ""

# Test counter
PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local path="$2"
    local expected_status="${3:-200}"
    local method="${4:-GET}"
    
    echo -n "  ${name}... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${DEPLOYMENT_URL}${path}" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${DEPLOYMENT_URL}${path}" 2>&1)
    fi
    
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $status_code)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected $expected_status, got $status_code)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# 1. Health Check
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🏥 Health Check${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if test_endpoint "Health endpoint" "/health" 200; then
    # Parse JSON response
    response=$(curl -s "${DEPLOYMENT_URL}/health")
    echo -e "     Response: ${BLUE}${response}${NC}"
fi
echo ""

# 2. API Documentation
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📚 API Documentation${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "Swagger UI" "/docs" 200
test_endpoint "OpenAPI JSON" "/openapi.json" 200
echo ""

# 3. Frontend Pages
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🌐 Frontend Pages${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "Login page" "/" 200
test_endpoint "Dashboard" "/dashboard.html" 200
test_endpoint "Kanban" "/kanban.html" 200
test_endpoint "Keywords" "/keywords.html" 200
test_endpoint "Profile" "/profile.html" 200
echo ""

# 4. API Endpoints (Unauthenticated)
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔓 Unauthenticated API${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "Register (no data)" "/api/v1/auth/register" 422 "POST"
test_endpoint "Login (no data)" "/api/v1/auth/login" 422 "POST"
test_endpoint "Bids list (unauthorized)" "/api/v1/bids/" 401
echo ""

# 5. Static Assets
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📦 Static Assets${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_endpoint "CSS (variables)" "/css/variables.css" 200
test_endpoint "CSS (components)" "/css/components.css" 200
test_endpoint "JS (utils)" "/js/utils.js" 200
test_endpoint "JS (api)" "/js/api.js" 200
echo ""

# 6. CORS Headers
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔐 Security Headers${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -n "  CORS headers... "
cors_header=$(curl -s -I "${DEPLOYMENT_URL}/health" | grep -i "access-control-allow-origin" || echo "")
if [ -n "$cors_header" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo -e "     ${BLUE}${cors_header}${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARN${NC} (CORS header not found)"
fi

echo -n "  X-Frame-Options... "
xfo_header=$(curl -s -I "${DEPLOYMENT_URL}/" | grep -i "x-frame-options" || echo "")
if [ -n "$xfo_header" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo -e "     ${BLUE}${xfo_header}${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARN${NC} (X-Frame-Options not found)"
fi

echo -n "  X-Content-Type-Options... "
xcto_header=$(curl -s -I "${DEPLOYMENT_URL}/" | grep -i "x-content-type-options" || echo "")
if [ -n "$xcto_header" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    echo -e "     ${BLUE}${xcto_header}${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARN${NC} (X-Content-Type-Options not found)"
fi
echo ""

# Summary
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📊 Summary${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TOTAL=$((PASSED + FAILED))
PASS_RATE=$((PASSED * 100 / TOTAL))

echo ""
echo -e "  ${GREEN}Passed: ${PASSED}${NC}"
echo -e "  ${RED}Failed: ${FAILED}${NC}"
echo -e "  Total:  ${TOTAL}"
echo -e "  Pass Rate: ${PASS_RATE}%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 모든 테스트 통과!${NC}"
    echo ""
    echo -e "${BLUE}다음 단계:${NC}"
    echo -e "  1. 브라우저에서 수동 테스트: ${DEPLOYMENT_URL}"
    echo -e "  2. 로그인/회원가입 동작 확인"
    echo -e "  3. Dashboard 데이터 로딩 확인"
    echo -e "  4. 문제 없으면 프로덕션 배포 진행"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  일부 테스트 실패${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  1. Vercel 로그 확인: ${BLUE}vercel logs --follow${NC}"
    echo -e "  2. 환경 변수 확인: ${BLUE}vercel env ls${NC}"
    echo -e "  3. 데이터베이스 연결 확인"
    echo -e "  4. Redis 연결 확인"
    echo ""
    exit 1
fi
