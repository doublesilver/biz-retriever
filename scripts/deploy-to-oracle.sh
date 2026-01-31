#!/bin/bash

###############################################################################
# Biz-Retriever Oracle Cloud Deployment Script
# 
# 용도: Oracle Cloud Ampere A1 인스턴스에 자동 배포
# 작성자: doublesilver
# 날짜: 2026-01-31
###############################################################################

set -e  # 에러 발생 시 즉시 중단

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 배포 시작 시간
START_TIME=$(date +%s)

echo "======================================================================"
echo "  Biz-Retriever Oracle Cloud Deployment"
echo "======================================================================"
echo ""

###############################################################################
# 1. 사전 확인
###############################################################################

log_info "Step 1/10: 환경 확인 중..."

# OS 확인
if [[ ! -f /etc/os-release ]]; then
    log_error "지원되지 않는 운영체제입니다."
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    log_warning "Ubuntu가 아닌 OS입니다: $ID"
fi

log_success "OS: $PRETTY_NAME"

# 아키텍처 확인
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" ]] && [[ "$ARCH" != "x86_64" ]]; then
    log_error "지원되지 않는 아키텍처: $ARCH"
    exit 1
fi

log_success "Architecture: $ARCH"

# CPU 및 메모리 확인
CPU_CORES=$(nproc)
TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')

log_success "CPU Cores: $CPU_CORES"
log_success "Total Memory: ${TOTAL_MEM}GB"

if [[ $TOTAL_MEM -lt 4 ]]; then
    log_warning "메모리가 부족합니다 (${TOTAL_MEM}GB). 최소 4GB 권장."
fi

# 디스크 공간 확인
AVAILABLE_DISK=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
log_success "Available Disk: ${AVAILABLE_DISK}GB"

if [[ $AVAILABLE_DISK -lt 20 ]]; then
    log_error "디스크 공간 부족 (${AVAILABLE_DISK}GB). 최소 20GB 필요."
    exit 1
fi

###############################################################################
# 2. Docker 확인 및 설치
###############################################################################

log_info "Step 2/10: Docker 확인 중..."

if ! command -v docker &> /dev/null; then
    log_warning "Docker가 설치되지 않았습니다. 설치를 시작합니다..."
    
    # Docker 설치
    curl -fsSL https://get.docker.com | sudo sh
    
    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker $USER
    
    log_success "Docker 설치 완료"
    log_warning "docker 그룹이 적용되려면 재로그인이 필요합니다."
    log_warning "이 스크립트를 종료하고 'exit' 후 다시 로그인한 뒤 재실행하세요."
    exit 0
else
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    log_success "Docker 버전: $DOCKER_VERSION"
fi

# Docker Compose 확인
if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose가 설치되지 않았습니다."
    exit 1
else
    COMPOSE_VERSION=$(docker compose version | awk '{print $4}')
    log_success "Docker Compose 버전: $COMPOSE_VERSION"
fi

###############################################################################
# 3. 프로젝트 디렉토리 확인
###############################################################################

log_info "Step 3/10: 프로젝트 디렉토리 확인 중..."

PROJECT_DIR="$HOME/biz-retriever"

if [[ ! -d "$PROJECT_DIR" ]]; then
    log_warning "프로젝트 디렉토리가 없습니다. Git clone을 시작합니다..."
    
    # Git 확인
    if ! command -v git &> /dev/null; then
        log_info "Git 설치 중..."
        sudo apt update
        sudo apt install -y git
    fi
    
    # 프로젝트 Clone
    cd ~
    git clone https://github.com/doublesilver/biz-retriever.git
    
    log_success "프로젝트 Clone 완료: $PROJECT_DIR"
else
    log_success "프로젝트 디렉토리 존재: $PROJECT_DIR"
    
    # 최신 코드로 업데이트
    log_info "최신 코드로 업데이트 중..."
    cd "$PROJECT_DIR"
    git pull origin master
    log_success "코드 업데이트 완료"
fi

cd "$PROJECT_DIR"

###############################################################################
# 4. 환경 변수 파일 확인
###############################################################################

log_info "Step 4/10: 환경 변수 파일 확인 중..."

if [[ ! -f ".env" ]]; then
    log_warning ".env 파일이 없습니다."
    
    if [[ -f ".env.example" ]]; then
        log_info ".env.example을 복사합니다..."
        cp .env.example .env
        log_warning ".env 파일을 편집해야 합니다:"
        log_warning "  nano .env"
        log_warning ""
        log_warning "필수 설정 항목:"
        log_warning "  - POSTGRES_PASSWORD"
        log_warning "  - REDIS_PASSWORD"
        log_warning "  - SECRET_KEY (python scripts/generate_secret_key.py)"
        log_warning "  - G2B_API_KEY"
        log_warning "  - GEMINI_API_KEY"
        log_warning ""
        log_error "환경 변수 설정 후 스크립트를 다시 실행하세요."
        exit 1
    else
        log_error ".env.example 파일도 없습니다. 프로젝트 구조를 확인하세요."
        exit 1
    fi
else
    log_success ".env 파일 존재"
    
    # 필수 변수 확인
    source .env
    
    REQUIRED_VARS=(
        "POSTGRES_PASSWORD"
        "SECRET_KEY"
        "G2B_API_KEY"
    )
    
    MISSING_VARS=()
    
    for VAR in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!VAR}" ]]; then
            MISSING_VARS+=("$VAR")
        fi
    done
    
    if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
        log_error "누락된 환경 변수:"
        for VAR in "${MISSING_VARS[@]}"; do
            echo "  - $VAR"
        done
        log_error ".env 파일을 편집하세요: nano .env"
        exit 1
    fi
    
    log_success "필수 환경 변수 확인 완료"
fi

###############################################################################
# 5. 기존 컨테이너 중지
###############################################################################

log_info "Step 5/10: 기존 컨테이너 중지 중..."

if docker compose ps | grep -q "Up"; then
    log_warning "실행 중인 컨테이너가 있습니다. 중지합니다..."
    docker compose down
    log_success "컨테이너 중지 완료"
else
    log_success "실행 중인 컨테이너 없음"
fi

###############################################################################
# 6. 데이터 디렉토리 생성
###############################################################################

log_info "Step 6/10: 데이터 디렉토리 생성 중..."

mkdir -p data/postgres data/redis logs

log_success "데이터 디렉토리 생성 완료"

###############################################################################
# 7. Docker 이미지 빌드
###############################################################################

log_info "Step 7/10: Docker 이미지 빌드 시작..."
log_warning "이 단계는 30-60분 소요될 수 있습니다 (ARM 아키텍처)."
log_info "빌드 로그는 /tmp/docker-build.log에 저장됩니다."

BUILD_START=$(date +%s)

# 빌드 시작
docker compose build --progress=plain > /tmp/docker-build.log 2>&1 &
BUILD_PID=$!

# 진행 상태 표시
log_info "빌드 PID: $BUILD_PID"
log_info "실시간 로그 확인: tail -f /tmp/docker-build.log"

# 빌드 완료 대기 (타임아웃: 90분)
TIMEOUT=5400  # 90분
ELAPSED=0

while kill -0 $BUILD_PID 2>/dev/null; do
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        log_error "빌드 타임아웃 (90분 초과)"
        kill $BUILD_PID
        exit 1
    fi
    
    # 10분마다 상태 출력
    if [[ $((ELAPSED % 600)) -eq 0 ]]; then
        MINUTES=$((ELAPSED / 60))
        log_info "빌드 진행 중... (${MINUTES}분 경과)"
    fi
done

# 빌드 결과 확인
wait $BUILD_PID
BUILD_EXIT_CODE=$?

BUILD_END=$(date +%s)
BUILD_DURATION=$((BUILD_END - BUILD_START))
BUILD_MINUTES=$((BUILD_DURATION / 60))

if [[ $BUILD_EXIT_CODE -eq 0 ]]; then
    log_success "이미지 빌드 완료 (소요 시간: ${BUILD_MINUTES}분)"
else
    log_error "이미지 빌드 실패 (Exit Code: $BUILD_EXIT_CODE)"
    log_error "로그 확인: cat /tmp/docker-build.log"
    exit 1
fi

###############################################################################
# 8. 컨테이너 시작
###############################################################################

log_info "Step 8/10: 컨테이너 시작 중..."

docker compose up -d

log_success "컨테이너 시작 완료"

# 컨테이너 상태 확인 (30초 대기)
log_info "컨테이너 Health Check 대기 중 (30초)..."
sleep 30

docker compose ps

###############################################################################
# 9. 데이터베이스 마이그레이션
###############################################################################

log_info "Step 9/10: 데이터베이스 마이그레이션 실행 중..."

# API 컨테이너가 준비될 때까지 대기
MAX_WAIT=60
WAITED=0

while ! docker compose exec -T api alembic current &>/dev/null; do
    sleep 5
    WAITED=$((WAITED + 5))
    
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        log_error "API 컨테이너가 준비되지 않았습니다 (60초 초과)"
        log_error "로그 확인: docker compose logs api"
        exit 1
    fi
done

# 마이그레이션 실행
docker compose exec -T api alembic upgrade head

if [[ $? -eq 0 ]]; then
    log_success "데이터베이스 마이그레이션 완료"
else
    log_error "마이그레이션 실패"
    docker compose logs api
    exit 1
fi

###############################################################################
# 10. Health Check
###############################################################################

log_info "Step 10/10: Health Check 실행 중..."

# Health endpoint 확인
sleep 5

HEALTH_RESPONSE=$(curl -s http://localhost:8000/health || echo "FAIL")

if [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
    log_success "Health Check 성공!"
    echo "$HEALTH_RESPONSE"
else
    log_error "Health Check 실패"
    log_error "응답: $HEALTH_RESPONSE"
    log_error "API 로그 확인:"
    docker compose logs --tail=50 api
    exit 1
fi

###############################################################################
# 배포 완료
###############################################################################

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))
TOTAL_MINUTES=$((TOTAL_DURATION / 60))

echo ""
echo "======================================================================"
echo "  배포 완료!"
echo "======================================================================"
echo ""
log_success "총 소요 시간: ${TOTAL_MINUTES}분"
echo ""
echo "접속 정보:"
echo "  - API 문서: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  - Health Check: http://$(hostname -I | awk '{print $1}'):8000/health"
echo ""
echo "다음 단계:"
echo "  1. Oracle Cloud 방화벽에서 포트 80, 443, 8000 오픈"
echo "  2. 외부에서 접속 테스트: http://<PUBLIC_IP>:8000/docs"
echo "  3. (선택사항) Nginx Reverse Proxy 설정"
echo "  4. (선택사항) 도메인 연결 및 SSL 인증서 발급"
echo ""
log_info "로그 확인: docker compose logs -f"
log_info "컨테이너 상태: docker compose ps"
echo ""

exit 0
