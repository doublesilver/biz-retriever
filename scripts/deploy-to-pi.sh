#!/bin/bash

###############################################################################
# Biz-Retriever 라즈베리파이 배포 스크립트
# 작성일: 2026-01-31
# 설명: 보안 강화 업데이트 자동 배포
###############################################################################

set -e  # 에러 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 라즈베리파이 정보
PI_USER="admin"
PI_HOST="100.75.72.6"
PI_PROJECT_DIR="/home/admin/projects/biz-retriever"

# 함수: 로그 출력
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 함수: SSH 명령 실행
ssh_exec() {
    ssh -o StrictHostKeyChecking=no ${PI_USER}@${PI_HOST} "$1"
}

# 함수: 배포 시작
deploy_start() {
    log_info "========================================="
    log_info "Biz-Retriever 라즈베리파이 배포 시작"
    log_info "========================================="
    echo ""
    log_info "배포 대상: ${PI_USER}@${PI_HOST}"
    log_info "프로젝트 디렉토리: ${PI_PROJECT_DIR}"
    echo ""
}

# 함수: 1단계 - 연결 테스트
step1_connection_test() {
    log_info "Step 1: 라즈베리파이 연결 테스트..."
    
    if ssh_exec "echo 'Connection OK'"; then
        log_success "라즈베리파이 연결 성공"
    else
        log_error "라즈베리파이 연결 실패. SSH 설정을 확인하세요."
        exit 1
    fi
    echo ""
}

# 함수: 2단계 - 현재 상태 백업
step2_backup_current_state() {
    log_info "Step 2: 현재 상태 백업..."
    
    BACKUP_FILE="deployment_backup_$(date +%Y%m%d_%H%M%S).log"
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose ps > ${BACKUP_FILE}"
    ssh_exec "cd ${PI_PROJECT_DIR} && git log --oneline -1 >> ${BACKUP_FILE}"
    
    log_success "현재 상태 백업 완료"
    echo ""
}

# 함수: 3단계 - Git Pull
step3_git_pull() {
    log_info "Step 3: 최신 코드 가져오기..."
    
    log_info "현재 커밋:"
    ssh_exec "cd ${PI_PROJECT_DIR} && git log --oneline -1"
    
    log_info "Git pull 실행 중..."
    ssh_exec "cd ${PI_PROJECT_DIR} && git pull origin master"
    
    log_info "새 커밋:"
    ssh_exec "cd ${PI_PROJECT_DIR} && git log --oneline -1"
    
    log_success "Git pull 완료"
    echo ""
}

# 함수: 4단계 - 데이터베이스 마이그레이션
step4_database_migration() {
    log_info "Step 4: 데이터베이스 마이그레이션..."
    
    log_info "현재 마이그레이션 상태:"
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose exec -T api alembic current" || true
    
    log_info "마이그레이션 실행 중..."
    if ssh_exec "cd ${PI_PROJECT_DIR} && docker compose exec -T api alembic upgrade head"; then
        log_success "데이터베이스 마이그레이션 성공"
    else
        log_error "데이터베이스 마이그레이션 실패"
        log_warning "수동으로 마이그레이션을 확인하세요: ssh ${PI_USER}@${PI_HOST}"
        exit 1
    fi
    echo ""
}

# 함수: 5단계 - Docker 서비스 재시작
step5_restart_services() {
    log_info "Step 5: Docker 서비스 재시작..."
    
    log_info "기존 서비스 중지 중..."
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose down"
    
    log_info "새 서비스 시작 중..."
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose -f docker-compose.pi.yml up -d"
    
    log_info "서비스 시작 대기 중 (30초)..."
    sleep 30
    
    log_success "Docker 서비스 재시작 완료"
    echo ""
}

# 함수: 6단계 - Health Check
step6_health_check() {
    log_info "Step 6: Health Check..."
    
    log_info "Docker 서비스 상태:"
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose ps"
    
    log_info "API Health Check (로컬):"
    if ssh_exec "curl -f http://localhost:8000/health"; then
        log_success "API Health Check 성공"
    else
        log_error "API Health Check 실패"
        exit 1
    fi
    
    echo ""
    log_info "외부 URL Health Check:"
    if curl -f https://leeeunseok.tail32c3e2.ts.net/health 2>/dev/null; then
        log_success "외부 URL Health Check 성공"
    else
        log_warning "외부 URL Health Check 실패 (Tailscale Funnel 확인 필요)"
    fi
    
    echo ""
}

# 함수: 7단계 - 로그 확인
step7_check_logs() {
    log_info "Step 7: 서비스 로그 확인..."
    
    log_info "최근 API 로그 (30줄):"
    ssh_exec "cd ${PI_PROJECT_DIR} && docker compose logs --tail=30 api"
    
    echo ""
    log_info "에러 로그 확인:"
    error_count=$(ssh_exec "cd ${PI_PROJECT_DIR} && docker compose logs | grep -i 'error\\|exception\\|failed' | wc -l")
    
    if [ "$error_count" -eq 0 ]; then
        log_success "에러 로그 없음"
    else
        log_warning "에러 로그 ${error_count}건 발견. 확인이 필요합니다."
    fi
    
    echo ""
}

# 함수: 배포 완료
deploy_complete() {
    echo ""
    log_info "========================================="
    log_success "배포 완료!"
    log_info "========================================="
    echo ""
    
    log_info "서비스 URL:"
    echo "  - API: https://leeeunseok.tail32c3e2.ts.net/"
    echo "  - Swagger UI: https://leeeunseok.tail32c3e2.ts.net/docs"
    echo "  - Grafana: http://${PI_HOST}:3000"
    echo ""
    
    log_info "주요 변경사항:"
    echo "  - OAuth2 제거 (Kakao, Naver)"
    echo "  - 계정 잠금 (5회 실패 → 30분)"
    echo "  - 로그아웃 엔드포인트 추가"
    echo "  - Access Token 유효기간 단축 (8일 → 15분)"
    echo ""
    
    log_info "다음 단계:"
    echo "  1. 브라우저에서 https://leeeunseok.tail32c3e2.ts.net/docs 접속"
    echo "  2. 회원가입/로그인 테스트"
    echo "  3. 로그아웃 테스트"
    echo "  4. 계정 잠금 기능 테스트 (선택)"
    echo ""
}

# 메인 실행
main() {
    deploy_start
    
    step1_connection_test
    step2_backup_current_state
    step3_git_pull
    step4_database_migration
    step5_restart_services
    step6_health_check
    step7_check_logs
    
    deploy_complete
}

# 스크립트 실행
main "$@"
