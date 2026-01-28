# Biz-Retriever 라즈베리파이 배포 명령어 (복사-붙여넣기용)

## 1단계: 라즈베리파이 SSH 접속
```bash
ssh admin@100.75.72.6
# 비밀번호: qwer1234
```

## 2단계: 프로젝트 클론 및 설정
```bash
# 프로젝트 디렉토리로 이동
cd /home/admin/projects

# 기존 디렉토리가 있다면 삭제
rm -rf biz-retriever

# GitHub에서 최신 코드 클론
git clone https://github.com/doublesilver/biz-retriever.git
cd biz-retriever

# 환경 변수 파일 생성
cat > .env << 'EOF'
POSTGRES_DB=biz_retriever
POSTGRES_USER=admin
POSTGRES_PASSWORD=BizRetriever2026!SecurePass

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

GEMINI_API_KEY=AIzaSyDH7PjcBbsQiTqnpoeQzFNdRXqj_yFHTzk
G2B_API_KEY=844ea00e83f650cd8a9fe556497d225623120e0a166209989d53a3ccb42bb873
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

ENVIRONMENT=production
LOG_LEVEL=INFO

REDIS_HOST=redis
REDIS_PORT=6379

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF

# 필요한 디렉토리 생성
mkdir -p data/{postgres,redis,nginx-proxy-manager,letsencrypt,backups}
mkdir -p logs

# 스크립트 실행 권한 부여
chmod +x scripts/*.sh
```

## 3단계: Docker 설치 (미설치 시만)
```bash
# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "Docker 설치 중..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    sudo apt-get install -y docker-compose
    
    # 재로그인 필요
    echo "Docker 설치 완료! 재로그인 후 계속하세요."
    exit
fi
```

## 4단계: 배포 실행
```bash
# 기존 컨테이너 중지 (있다면)
docker-compose -f docker-compose.pi.yml down 2>/dev/null || true

# 이미지 빌드 및 컨테이너 시작
docker-compose -f docker-compose.pi.yml up -d --build

# 로그 확인 (Ctrl+C로 종료)
docker-compose -f docker-compose.pi.yml logs -f
```

## 5단계: 상태 확인
```bash
# 컨테이너 상태
docker-compose -f docker-compose.pi.yml ps

# API 헬스 체크
curl http://localhost:8000/health

# 리소스 사용량
./scripts/monitor.sh
```

## 서비스 접속 (윈도우에서)
- API: http://100.75.72.6:8000
- API Docs: http://100.75.72.6:8000/docs
- Nginx PM: http://100.75.72.6:81 (admin@example.com / changeme)

## 유용한 명령어
```bash
# 로그 확인
docker-compose -f docker-compose.pi.yml logs -f api

# 재시작
docker-compose -f docker-compose.pi.yml restart

# 중지
docker-compose -f docker-compose.pi.yml stop

# 완전 삭제
docker-compose -f docker-compose.pi.yml down -v

# DB 백업
./scripts/backup-db.sh
```
