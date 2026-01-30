#!/bin/bash

# ==============================================
# Biz-Retriever Deployment Verification Script
# ==============================================
# Comprehensive system check for Raspberry Pi deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Helper functions
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

check_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# ==============================================
# 1. Environment Configuration
# ==============================================
print_header "1. Environment Configuration"

if [ -f .env ]; then
    check_pass ".env file exists"
    
    # Check required variables
    required_vars=("SECRET_KEY" "POSTGRES_PASSWORD" "GEMINI_API_KEY" "G2B_API_KEY")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=your-" .env && ! grep -q "^${var}=$" .env; then
            check_pass "$var is configured"
        else
            check_fail "$var is missing or not configured"
        fi
    done
else
    check_fail ".env file not found. Copy .env.example to .env first"
fi

# ==============================================
# 2. Docker Services
# ==============================================
print_header "2. Docker Services"

if command -v docker &> /dev/null; then
    check_pass "Docker is installed"
else
    check_fail "Docker is not installed"
fi

if command -v docker-compose &> /dev/null; then
    check_pass "Docker Compose is installed"
else
    check_fail "Docker Compose is not installed"
fi

# Check containers
expected_containers=("api" "db" "redis" "celery_worker" "celery_beat" "nginx" "prometheus" "grafana" "alertmanager" "postgres_exporter" "redis_exporter")
running_count=0

for container in "${expected_containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}\$"; then
        check_pass "Container '${container}' is running"
        ((running_count++))
    else
        check_fail "Container '${container}' is not running"
    fi
done

if [ $running_count -eq ${#expected_containers[@]} ]; then
    check_pass "All ${#expected_containers[@]} containers are running"
else
    check_fail "Only $running_count/${#expected_containers[@]} containers are running"
fi

# ==============================================
# 3. API Health Check
# ==============================================
print_header "3. API Health Check"

if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    response=$(curl -s http://localhost:8000/health)
    if echo "$response" | grep -q '"status":"ok"'; then
        check_pass "API health endpoint returns OK"
    else
        check_fail "API health endpoint returned unexpected response"
    fi
else
    check_fail "API health endpoint unreachable"
fi

# Check Prometheus metrics
if curl -f -s http://localhost:8000/metrics > /dev/null 2>&1; then
    check_pass "Prometheus metrics endpoint accessible"
else
    check_fail "Prometheus metrics endpoint not accessible"
fi

# ==============================================
# 4. Database Connectivity
# ==============================================
print_header "4. Database Connectivity"

if docker-compose -f docker-compose.pi.yml exec -T db pg_isready > /dev/null 2>&1; then
    check_pass "PostgreSQL is accepting connections"
else
    check_fail "PostgreSQL is not accepting connections"
fi

# Check tables exist
table_count=$(docker-compose -f docker-compose.pi.yml exec -T db psql -U admin -d biz_retriever -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

if [ "$table_count" -gt 10 ]; then
    check_pass "Database has $table_count tables (migration complete)"
else
    check_warn "Database has only $table_count tables (migrations may not be complete)"
fi

# ==============================================
# 5. Redis Connectivity
# ==============================================
print_header "5. Redis Connectivity"

if docker-compose -f docker-compose.pi.yml exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    check_pass "Redis is responding"
else
    check_fail "Redis is not responding"
fi

# ==============================================
# 6. Celery Workers
# ==============================================
print_header "6. Celery Workers"

if docker-compose -f docker-compose.pi.yml logs celery_worker 2>/dev/null | grep -q "ready"; then
    check_pass "Celery worker is ready"
else
    check_fail "Celery worker not ready"
fi

if docker-compose -f docker-compose.pi.yml logs celery_beat 2>/dev/null | grep -q "beat"; then
    check_pass "Celery beat is running"
else
    check_warn "Celery beat may not be running"
fi

# ==============================================
# 7. Frontend Accessibility
# ==============================================
print_header "7. Frontend Accessibility"

if curl -f -s -I http://localhost:8081 > /dev/null 2>&1; then
    check_pass "Frontend is accessible on port 8081"
else
    check_fail "Frontend is not accessible on port 8081"
fi

# ==============================================
# 8. Monitoring Stack
# ==============================================
print_header "8. Monitoring Stack"

# Prometheus
if curl -f -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    check_pass "Prometheus is healthy"
else
    check_fail "Prometheus is not accessible"
fi

# Grafana
if curl -f -s -I http://localhost:3000/api/health > /dev/null 2>&1; then
    check_pass "Grafana is accessible"
else
    check_fail "Grafana is not accessible"
fi

# Alertmanager
if curl -f -s http://localhost:9093/-/healthy > /dev/null 2>&1; then
    check_pass "Alertmanager is healthy"
else
    check_fail "Alertmanager is not accessible"
fi

# ==============================================
# 9. SSL Certificate
# ==============================================
print_header "9. SSL Certificate"

# Check if SSL certificate files exist
if [ -f "/etc/letsencrypt/live/leeeunseok.tail32c3e2.ts.net/fullchain.pem" ]; then
    check_pass "SSL certificate file exists"
    
    # Check expiration
    expiry_date=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/leeeunseok.tail32c3e2.ts.net/fullchain.pem 2>/dev/null | cut -d= -f2)
    if [ -n "$expiry_date" ]; then
        check_pass "SSL certificate valid until: $expiry_date"
    fi
else
    check_warn "SSL certificate not found (may be using Nginx Proxy Manager)"
fi

# ==============================================
# 10. Disk Usage
# ==============================================
print_header "10. Disk Usage"

disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 80 ]; then
    check_pass "Disk usage is ${disk_usage}% (healthy)"
else
    check_warn "Disk usage is ${disk_usage}% (consider cleanup)"
fi

# ==============================================
# 11. Memory Usage
# ==============================================
print_header "11. Memory Usage"

mem_usage=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ "$mem_usage" -lt 90 ]; then
    check_pass "Memory usage is ${mem_usage}% (healthy)"
else
    check_warn "Memory usage is ${mem_usage}% (high)"
fi

# ==============================================
# 12. Docker Volume Space
# ==============================================
print_header "12. Docker Volume Space"

docker_volumes=$(docker volume ls -q | wc -l)
check_pass "Docker has $docker_volumes volumes"

# ==============================================
# 13. Backup Configuration
# ==============================================
print_header "13. Backup Configuration"

if [ -f "scripts/backup-db.sh" ]; then
    check_pass "Backup script exists"
    
    if crontab -l 2>/dev/null | grep -q "backup-db.sh"; then
        check_pass "Backup cron job is configured"
    else
        check_warn "Backup cron job not found. Add to crontab: 0 3 * * * $(pwd)/scripts/backup-db.sh"
    fi
else
    check_fail "Backup script not found"
fi

# ==============================================
# Summary
# ==============================================
print_header "Verification Summary"

TOTAL=$((PASSED + FAILED))
PASS_RATE=$((PASSED * 100 / TOTAL))

echo ""
echo "Total Checks: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Pass Rate: ${PASS_RATE}%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✓ ALL CHECKS PASSED - DEPLOYMENT SUCCESSFUL"
    echo "==========================================${NC}"
    exit 0
elif [ $PASS_RATE -ge 80 ]; then
    echo -e "${YELLOW}=========================================="
    echo "⚠ DEPLOYMENT MOSTLY SUCCESSFUL ($PASS_RATE% pass rate)"
    echo "  Review failed checks and warnings above"
    echo "==========================================${NC}"
    exit 1
else
    echo -e "${RED}=========================================="
    echo "✗ DEPLOYMENT FAILED ($PASS_RATE% pass rate)"
    echo "  Critical issues detected - review logs"
    echo "==========================================${NC}"
    exit 2
fi
