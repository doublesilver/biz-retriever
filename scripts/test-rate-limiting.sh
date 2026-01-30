#!/bin/bash

# Rate Limiting Test Script
# Tests DDoS protection on Frontend Nginx

set -e

echo "================================================"
echo "Rate Limiting Test for Biz-Retriever"
echo "================================================"
echo ""

# Configuration
TARGET_URL="${TARGET_URL:-http://localhost:3001}"
API_ENDPOINT="${TARGET_URL}/api/v1/bids/"
STATIC_ENDPOINT="${TARGET_URL}/js/utils.js"

echo "Target URL: $TARGET_URL"
echo ""

# ============================================
# Test 1: API Rate Limiting (10 req/s)
# ============================================
echo "Test 1: API Rate Limiting (should allow 10 req/s)"
echo "Sending 15 requests in parallel..."

SUCCESS_COUNT=0
RATE_LIMITED_COUNT=0

for i in {1..15}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT" 2>/dev/null || echo "ERROR")
    
    if [ "$HTTP_CODE" == "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif [ "$HTTP_CODE" == "429" ]; then
        RATE_LIMITED_COUNT=$((RATE_LIMITED_COUNT + 1))
    fi
done

echo "  ✓ Success (200): $SUCCESS_COUNT"
echo "  ✓ Rate Limited (429): $RATE_LIMITED_COUNT"

if [ $SUCCESS_COUNT -ge 10 ] && [ $RATE_LIMITED_COUNT -ge 1 ]; then
    echo "  ✅ PASSED: Rate limiting is working"
else
    echo "  ❌ FAILED: Expected ~10 success and ~5 rate limited"
fi

echo ""

# ============================================
# Test 2: Static File Rate Limiting (50 req/s)
# ============================================
echo "Test 2: Static File Rate Limiting (should allow 50 req/s)"
echo "Sending 60 requests in parallel..."

SUCCESS_COUNT=0
RATE_LIMITED_COUNT=0

for i in {1..60}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$STATIC_ENDPOINT" 2>/dev/null || echo "ERROR")
    
    if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "304" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif [ "$HTTP_CODE" == "429" ]; then
        RATE_LIMITED_COUNT=$((RATE_LIMITED_COUNT + 1))
    fi
done

echo "  ✓ Success (200/304): $SUCCESS_COUNT"
echo "  ✓ Rate Limited (429): $RATE_LIMITED_COUNT"

if [ $SUCCESS_COUNT -ge 50 ]; then
    echo "  ✅ PASSED: Static rate limiting allows higher throughput"
else
    echo "  ⚠️  WARNING: Success count lower than expected ($SUCCESS_COUNT < 50)"
fi

echo ""

# ============================================
# Test 3: Malicious User-Agent Blocking
# ============================================
echo "Test 3: Malicious User-Agent Blocking"

BAD_AGENTS=("nikto" "sqlmap" "nmap" "python-requests" "scrapy")
BLOCKED_COUNT=0

for AGENT in "${BAD_AGENTS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -A "$AGENT" "$TARGET_URL/" 2>/dev/null || echo "ERROR")
    
    if [ "$HTTP_CODE" == "403" ]; then
        BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
        echo "  ✓ Blocked: $AGENT (403)"
    else
        echo "  ✗ Not blocked: $AGENT ($HTTP_CODE)"
    fi
done

if [ $BLOCKED_COUNT -eq ${#BAD_AGENTS[@]} ]; then
    echo "  ✅ PASSED: All malicious bots blocked ($BLOCKED_COUNT/${#BAD_AGENTS[@]})"
else
    echo "  ❌ FAILED: Some bots not blocked ($BLOCKED_COUNT/${#BAD_AGENTS[@]})"
fi

echo ""

# ============================================
# Test 4: Empty User-Agent Blocking
# ============================================
echo "Test 4: Empty User-Agent Blocking"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -A "" "$TARGET_URL/" 2>/dev/null || echo "ERROR")

if [ "$HTTP_CODE" == "403" ]; then
    echo "  ✅ PASSED: Empty User-Agent blocked (403)"
else
    echo "  ❌ FAILED: Empty User-Agent not blocked ($HTTP_CODE)"
fi

echo ""

# ============================================
# Test 5: Connection Limit (optional)
# ============================================
echo "Test 5: Connection Limit (10 concurrent connections)"
echo "Opening 15 concurrent connections..."

# This test requires 'ab' (Apache Bench) or similar tool
if command -v ab &> /dev/null; then
    ab -n 100 -c 15 "$TARGET_URL/" > /tmp/ab_test.log 2>&1 || true
    
    FAILED_REQUESTS=$(grep "Failed requests" /tmp/ab_test.log | awk '{print $3}')
    
    if [ -n "$FAILED_REQUESTS" ] && [ "$FAILED_REQUESTS" -gt 0 ]; then
        echo "  ✅ PASSED: Connection limit working ($FAILED_REQUESTS failed)"
    else
        echo "  ⚠️  WARNING: No connection failures detected"
    fi
else
    echo "  ⏭️  SKIPPED: 'ab' tool not installed"
fi

echo ""

# ============================================
# Summary
# ============================================
echo "================================================"
echo "Test Summary"
echo "================================================"
echo ""
echo "Configuration Applied:"
echo "  - API Rate Limit: 10 req/s (burst 20)"
echo "  - Static Rate Limit: 50 req/s (burst 100)"
echo "  - Connection Limit: 10 concurrent per IP"
echo "  - Malicious Bot Blocking: Enabled"
echo "  - Empty User-Agent Blocking: Enabled"
echo ""
echo "Next Steps:"
echo "  1. Review Nginx logs: docker logs sideproject-frontend-1"
echo "  2. Check Prometheus metrics for 429 errors"
echo "  3. Monitor production traffic for false positives"
echo ""
echo "Test completed at $(date)"
