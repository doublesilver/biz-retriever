#!/bin/bash
# Biz-Retriever 라즈베리파이 배포 스크립트

set -e

echo "🚀 Biz-Retriever 배포 시작..."

# 1. 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 .env를 생성하세요."
    exit 1
fi

# 2. 필요한 디렉토리 생성
echo "📁 디렉토리 생성 중..."
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p data/nginx-proxy-manager
mkdir -p data/letsencrypt
mkdir -p data/backups
mkdir -p logs

# 3. Docker 및 Docker Compose 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되어 있지 않습니다."
    echo "다음 명령어로 설치하세요:"
    echo "curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "sudo sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되어 있지 않습니다."
    echo "다음 명령어로 설치하세요:"
    echo "sudo apt-get install -y docker-compose"
    exit 1
fi

# 4. 이전 컨테이너 정리 (선택사항)
read -p "기존 컨테이너를 정리하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 기존 컨테이너 정리 중..."
    docker-compose -f docker-compose.pi.yml down
fi

# 5. 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker-compose -f docker-compose.pi.yml build --no-cache

# 6. 컨테이너 시작
echo "▶️  컨테이너 시작 중..."
docker-compose -f docker-compose.pi.yml up -d

# 7. 상태 확인
echo "⏳ 서비스 시작 대기 중 (30초)..."
sleep 30

echo "📊 컨테이너 상태 확인..."
docker-compose -f docker-compose.pi.yml ps

# 8. 헬스 체크
echo "🏥 헬스 체크 중..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API 서버 정상 작동 중!"
else
    echo "⚠️  API 서버가 아직 준비되지 않았습니다. 로그를 확인하세요:"
    echo "docker-compose -f docker-compose.pi.yml logs api"
fi

# 9. 로그 확인 안내
echo ""
echo "✅ 배포 완료!"
echo ""
echo "📋 유용한 명령어:"
echo "  - 로그 확인: docker-compose -f docker-compose.pi.yml logs -f"
echo "  - 상태 확인: docker-compose -f docker-compose.pi.yml ps"
echo "  - 중지: docker-compose -f docker-compose.pi.yml stop"
echo "  - 재시작: docker-compose -f docker-compose.pi.yml restart"
echo "  - 완전 삭제: docker-compose -f docker-compose.pi.yml down -v"
echo ""
echo "🌐 서비스 접속:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Nginx PM: http://localhost:81 (admin@example.com / changeme)"
echo ""
