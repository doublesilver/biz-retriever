#!/bin/bash

# ============================================
# SSL/HTTPS 보안 검증 스크립트
# ============================================
#
# 목적: HTTPS 설정, 보안 헤더, SSL 인증서 검증
# 사용: bash scripts/verify-ssl.sh
#
# 검증 항목:
# 1. HTTP → HTTPS 리다이렉트
# 2. HTTPS 접속 가능 여부
# 3. 보안 헤더 (6가지)
# 4. SSL 인증서 유효성
# 5. 인증서 발급자 (Let's Encrypt)

set -e

# 도메인 설정
DOMAIN="leeeunseok.tail32c3e2.ts.net"
PORT=443

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 성공 메시지
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 함수: 실패 메시지
fail() {
    echo -e "${RED}❌ $1${NC}"
}

# 함수: 경고 메시지
warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 함수: 정보 메시지
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo ""
echo "=========================================="
echo "SSL/HTTPS 보안 검증"
echo "=========================================="
echo ""

# 1. HTTP → HTTPS 리다이렉트 확인
echo "1️⃣  HTTP → HTTPS 리다이렉트 확인"
echo "   요청: curl -I http://$DOMAIN"
echo ""

HTTP_RESPONSE=$(curl -s -I -w "\n%{http_code}" "http://$DOMAIN" 2>/dev/null || echo "000")
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -1)
HTTP_LOCATION=$(echo "$HTTP_RESPONSE" | grep -i "^location:" | head -1 || echo "")

if [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    success "HTTP 리다이렉트 상태: $HTTP_STATUS"
    if echo "$HTTP_LOCATION" | grep -q "https://"; then
        success "HTTPS로 리다이렉트됨: $HTTP_LOCATION"
    else
        fail "HTTPS로 리다이렉트되지 않음"
    fi
else
    fail "HTTP 리다이렉트 실패 (상태: $HTTP_STATUS)"
fi
echo ""

# 2. HTTPS 접속 확인
echo "2️⃣  HTTPS 접속 확인"
echo "   요청: curl -I https://$DOMAIN"
echo ""

HTTPS_RESPONSE=$(curl -s -I "https://$DOMAIN" 2>/dev/null || echo "")
HTTPS_STATUS=$(echo "$HTTPS_RESPONSE" | head -1)

if echo "$HTTPS_STATUS" | grep -q "200\|301\|302"; then
    success "HTTPS 접속 성공: $HTTPS_STATUS"
else
    fail "HTTPS 접속 실패"
    echo "$HTTPS_RESPONSE" | head -5
fi
echo ""

# 3. 보안 헤더 확인
echo "3️⃣  보안 헤더 확인"
echo ""

HEADERS=$(curl -s -I "https://$DOMAIN" 2>/dev/null)

# 3.1 HSTS 헤더
if echo "$HEADERS" | grep -qi "strict-transport-security"; then
    HSTS=$(echo "$HEADERS" | grep -i "strict-transport-security" | head -1)
    success "HSTS 헤더: $HSTS"
else
    fail "HSTS 헤더 없음"
fi

# 3.2 X-Frame-Options 헤더
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    XFO=$(echo "$HEADERS" | grep -i "x-frame-options" | head -1)
    success "X-Frame-Options 헤더: $XFO"
else
    fail "X-Frame-Options 헤더 없음"
fi

# 3.3 X-Content-Type-Options 헤더
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
    XCTO=$(echo "$HEADERS" | grep -i "x-content-type-options" | head -1)
    success "X-Content-Type-Options 헤더: $XCTO"
else
    fail "X-Content-Type-Options 헤더 없음"
fi

# 3.4 X-XSS-Protection 헤더
if echo "$HEADERS" | grep -qi "x-xss-protection"; then
    XXP=$(echo "$HEADERS" | grep -i "x-xss-protection" | head -1)
    success "X-XSS-Protection 헤더: $XXP"
else
    fail "X-XSS-Protection 헤더 없음"
fi

# 3.5 Referrer-Policy 헤더
if echo "$HEADERS" | grep -qi "referrer-policy"; then
    RP=$(echo "$HEADERS" | grep -i "referrer-policy" | head -1)
    success "Referrer-Policy 헤더: $RP"
else
    fail "Referrer-Policy 헤더 없음"
fi

# 3.6 Permissions-Policy 헤더
if echo "$HEADERS" | grep -qi "permissions-policy"; then
    PP=$(echo "$HEADERS" | grep -i "permissions-policy" | head -1)
    success "Permissions-Policy 헤더: $PP"
else
    fail "Permissions-Policy 헤더 없음"
fi

echo ""

# 4. SSL 인증서 유효성 확인
echo "4️⃣  SSL 인증서 유효성 확인"
echo ""

CERT_INFO=$(openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" < /dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

if [ -z "$CERT_INFO" ]; then
    fail "SSL 인증서 정보를 가져올 수 없음"
else
    echo "$CERT_INFO"
    
    # 만료 날짜 확인
    NOT_AFTER=$(echo "$CERT_INFO" | grep "notAfter" | cut -d= -f2)
    NOT_BEFORE=$(echo "$CERT_INFO" | grep "notBefore" | cut -d= -f2)
    
    success "인증서 발급일: $NOT_BEFORE"
    success "인증서 만료일: $NOT_AFTER"
    
    # 만료 여부 확인
    EXPIRY_DATE=$(date -d "$NOT_AFTER" +%s 2>/dev/null || echo "0")
    CURRENT_DATE=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_DATE - $CURRENT_DATE) / 86400 ))
    
    if [ "$DAYS_LEFT" -gt 0 ]; then
        success "인증서 유효 기간: $DAYS_LEFT일 남음"
    else
        fail "인증서 만료됨 ($((-$DAYS_LEFT))일 전)"
    fi
fi

echo ""

# 5. 인증서 발급자 확인
echo "5️⃣  인증서 발급자 확인"
echo ""

ISSUER=$(openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" < /dev/null 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null || echo "")

if [ -z "$ISSUER" ]; then
    fail "인증서 발급자 정보를 가져올 수 없음"
else
    echo "$ISSUER"
    
    if echo "$ISSUER" | grep -q "Let's Encrypt"; then
        success "Let's Encrypt 인증서 확인됨"
    else
        warn "Let's Encrypt 인증서가 아님"
    fi
fi

echo ""

# 6. 종합 검증 결과
echo "=========================================="
echo "검증 완료"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. 모든 항목이 ✅ 표시되었는지 확인"
echo "2. 보안 헤더 6가지 모두 설정되었는지 확인"
echo "3. Let's Encrypt 인증서 확인"
echo "4. 인증서 만료 날짜 확인 (30일 이상 남아있어야 함)"
echo ""
echo "문제 해결:"
echo "- HTTP 리다이렉트 실패: Nginx Proxy Manager에서 'Force SSL' 활성화 확인"
echo "- 보안 헤더 없음: Nginx Proxy Manager의 'Advanced' 탭에서 헤더 추가 확인"
echo "- SSL 인증서 오류: Let's Encrypt 발급 절차 재확인"
echo ""
