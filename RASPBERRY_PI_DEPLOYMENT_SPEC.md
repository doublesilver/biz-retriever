# Biz-Retriever 라즈베리파이 배포 사양서

> **프로젝트명**: Biz-Retriever on Raspberry Pi  
> **목표**: 라즈베리파이 4 (4GB RAM) 환경에 Biz-Retriever 서비스 배포  
> **작성일**: 2026-01-26

---

## 📋 프로젝트 개요

### 배경
- **현재 상황**: Biz-Retriever는 로컬 개발 환경에서만 실행 중
- **목표**: 라즈베리파이 4에 Docker Compose 기반으로 배포하여 24/7 운영
- **제약사항**: 4GB RAM 환경에서 안정적으로 작동해야 함

### 기대 효과
- ✅ **실제 운영 경험**: 프로덕션 환경 구축 및 관리
- ✅ **포트폴리오 강화**: 자체 서버 운영 경험 어필
- ✅ **DevOps 학습**: Docker, Nginx, 리소스 최적화 실무 경험
- ✅ **비용 절감**: 클라우드 비용 없이 전기세만

---

## 🖥️ 하드웨어 사양

### 라즈베리파이 4 스펙
```
- Model: Raspberry Pi 4 Model B
- RAM: 4GB (실장)
- CPU: BCM2711 (Cortex-A72) @ 2.0GHz (Overclocked)
- Architecture: ARM64 (aarch64)
- Storage: microSD (Log2Ram 설정 완료)
- Swap: 2GB (설정 완료)
- OS: Raspberry Pi OS 64-bit 또는 Ubuntu Server 22.04 LTS
```

### 리소스 가용성
- **총 RAM**: 4GB
- **시스템 예약**: ~500MB
- **가용 RAM**: ~3.5GB
- **Swap**: 2GB (성능 저하 최소화를 위해 최소 사용)

---

## 🏗️ 시스템 아키텍처

### 전체 구조도
```
┌─────────────────────────────────────────────────────────┐
│           Raspberry Pi 4 (4GB RAM, ARM64)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Docker Compose Network (pi-network)       │  │
│  │                                                     │  │
│  │  ┌──────────────────┐      ┌──────────────────┐  │  │
│  │  │  Nginx Proxy     │      │  PostgreSQL 15   │  │  │
│  │  │  Manager         │◄─────┤  (Alpine)        │  │  │
│  │  │  (Port 80/443)   │      │  (Port 5432)     │  │  │
│  │  │  [256MB]         │      │  [1GB]           │  │  │
│  │  └────────┬─────────┘      └──────────────────┘  │  │
│  │           │                                        │  │
│  │  ┌────────▼─────────┐      ┌──────────────────┐  │  │
│  │  │  Biz-Retriever   │      │     Redis        │  │  │
│  │  │  (FastAPI)       │◄─────┤  (Alpine)        │  │  │
│  │  │  (Port 8000)     │      │  (Port 6379)     │  │  │
│  │  │  [1.2GB]         │      │  [256MB]         │  │  │
│  │  └──────────────────┘      └──────────────────┘  │  │
│  │                                                     │  │
│  │  ┌──────────────────┐                              │  │
│  │  │  Celery Worker   │                              │  │
│  │  │  (Background)    │                              │  │
│  │  │  [512MB]         │                              │  │
│  │  └──────────────────┘                              │  │
│  │                                                     │  │
│  │  ┌──────────────────┐                              │  │
│  │  │  Celery Beat     │                              │  │
│  │  │  (Scheduler)     │                              │  │
│  │  │  [256MB]         │                              │  │
│  │  └──────────────────┘                              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  Total Allocated: ~3.5GB (여유: ~500MB)                 │
└─────────────────────────────────────────────────────────┘
```

### 컨테이너 구성

#### 1. Biz-Retriever (FastAPI)
- **이미지**: 커스텀 (Python 3.11-slim-bullseye)
- **포트**: 8000 (내부)
- **메모리**: 1.2GB
- **CPU**: 1.0
- **역할**: 메인 API 서버

#### 2. Celery Worker
- **이미지**: Biz-Retriever와 동일
- **메모리**: 512MB
- **CPU**: 0.5
- **역할**: 백그라운드 작업 (크롤링, AI 분석)

#### 3. Celery Beat
- **이미지**: Biz-Retriever와 동일
- **메모리**: 256MB
- **CPU**: 0.25
- **역할**: 스케줄러 (매일 08:00, 12:00, 18:00)

#### 4. PostgreSQL 15
- **이미지**: postgres:15-alpine
- **포트**: 5432 (내부만)
- **메모리**: 1GB
- **CPU**: 1.0
- **볼륨**: `/home/admin/projects/biz-retriever/data/postgres`

#### 5. Redis
- **이미지**: redis:7-alpine
- **포트**: 6379 (내부만)
- **메모리**: 256MB
- **CPU**: 0.25
- **볼륨**: `/home/admin/projects/biz-retriever/data/redis`

#### 6. Nginx Proxy Manager
- **이미지**: jc21/nginx-proxy-manager:latest
- **포트**: 80, 443, 81 (관리 UI)
- **메모리**: 256MB
- **CPU**: 0.25
- **역할**: 리버스 프록시, SSL 관리 (추후 도메인 연결 시)

---

## 📦 프로젝트 구조

```
/home/admin/projects/biz-retriever/
├── docker-compose.yml           # 전체 서비스 통합 설정
├── .env                         # 환경 변수
├── .env.example                 # 환경 변수 템플릿
├── Dockerfile                   # Biz-Retriever 이미지
├── requirements.txt             # Python 의존성
├── app/                         # FastAPI 애플리케이션
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── worker/
├── alembic/                     # DB 마이그레이션
├── data/                        # 영구 데이터 (gitignore)
│   ├── postgres/
│   ├── redis/
│   └── nginx-proxy-manager/
├── logs/                        # 로그 파일
└── scripts/
    ├── start.sh                 # 서비스 시작
    ├── stop.sh                  # 서비스 중지
    ├── backup-db.sh             # DB 백업
    └── monitor.sh               # 리소스 모니터링
```

---

## 🐳 Docker Compose 구성

### docker-compose.yml (최적화 버전)
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: biz-retriever-db
    restart: always
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-biz_retriever}
      POSTGRES_USER: ${POSTGRES_USER:-admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=C"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-admin}"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: biz-retriever-redis
    restart: always
    command: redis-server --maxmemory 200mb --maxmemory-policy allkeys-lru
    volumes:
      - ./data/redis:/data
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILDPLATFORM=linux/arm64
    container_name: biz-retriever-api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-biz_retriever}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SECRET_KEY=${SECRET_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - G2B_API_KEY=${G2B_API_KEY}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 1200M
          cpus: '1.0'
        reservations:
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: biz-retriever-worker
    restart: always
    command: celery -A app.worker.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-biz_retriever}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SECRET_KEY=${SECRET_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - G2B_API_KEY=${G2B_API_KEY}
      - SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  # Celery Beat (Scheduler)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: biz-retriever-beat
    restart: always
    command: celery -A app.worker.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-admin}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-biz_retriever}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  # Nginx Proxy Manager (Optional - 추후 도메인 연결 시)
  nginx-proxy-manager:
    image: jc21/nginx-proxy-manager:latest
    container_name: nginx-proxy-manager
    restart: always
    ports:
      - "80:80"
      - "443:443"
      - "81:81"
    environment:
      DB_SQLITE_FILE: "/data/database.sqlite"
    volumes:
      - ./data/nginx-proxy-manager:/data
      - ./data/letsencrypt:/etc/letsencrypt
    networks:
      - pi-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

networks:
  pi-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  npm-data:
```

---

## 🔧 Dockerfile 최적화

### Dockerfile (Multi-stage build for ARM64)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim-bullseye AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim-bullseye

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Run migrations on startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

---

## ⚙️ 리소스 최적화 전략

### 메모리 할당 (총 4GB 기준)

| 컨테이너 | Limit | Reservation | 우선순위 | 비고 |
|----------|-------|-------------|----------|------|
| PostgreSQL | 1GB | 512MB | 최고 | 데이터 안정성 |
| Biz-Retriever API | 1.2GB | 512MB | 최고 | 메인 서비스 |
| Celery Worker | 512MB | 256MB | 높음 | 크롤링/AI 작업 |
| Redis | 256MB | - | 중간 | LRU 정책 |
| Celery Beat | 256MB | - | 낮음 | 스케줄러만 |
| Nginx PM | 256MB | - | 낮음 | 프록시만 |
| **시스템 예약** | **~500MB** | - | - | OS + 여유 |

### CPU 할당
- PostgreSQL: 1.0 (전체 코어 사용 가능)
- API: 1.0
- Worker: 0.5 (동시성 2로 제한)
- 나머지: 0.25

### Swap 활용
- 2GB Swap 설정 완료
- 메모리 부족 시 자동 활용
- `vm.swappiness=10` 권장 (메모리 우선)

---

## 🚀 배포 절차

### 1. 라즈베리파이 준비
```bash
# Docker 설치 (미설치 시)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose 설치
sudo apt-get update
sudo apt-get install -y docker-compose

# 프로젝트 디렉토리 생성
mkdir -p /home/admin/projects/biz-retriever
cd /home/admin/projects/biz-retriever
```

### 2. 프로젝트 파일 전송
```bash
# 윈도우에서 라즈베리파이로 전송 (Tailscale IP 사용)
scp -r c:\sideproject/* admin@<TAILSCALE_IP>:/home/admin/projects/biz-retriever/
```

### 3. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env
nano .env

# 필수 환경 변수 설정
POSTGRES_PASSWORD=<강력한_비밀번호>
SECRET_KEY=<생성된_시크릿_키>
GEMINI_API_KEY=<your_gemini_key>
G2B_API_KEY=<your_g2b_key>
SLACK_WEBHOOK_URL=<your_slack_webhook>
```

### 4. 서비스 시작
```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps
```

### 5. 초기 설정
```bash
# DB 마이그레이션 확인
docker-compose exec api alembic current

# 관리자 계정 생성 (필요 시)
docker-compose exec api python scripts/create_admin.py
```

---

## 📊 모니터링

### 리소스 사용량 확인
```bash
# 실시간 모니터링
docker stats

# 특정 컨테이너 메모리 사용량
docker stats biz-retriever-api --no-stream
```

### 로그 관리
```bash
# 로그 확인
docker-compose logs -f api

# 로그 크기 제한 (docker-compose.yml에 추가)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 🔐 보안 설정

### 1. 방화벽
```bash
# UFW 설정 (필요 시)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 81/tcp  # Nginx PM 관리 UI
sudo ufw enable
```

### 2. 환경 변수 보안
- `.env` 파일은 절대 Git에 커밋하지 않음
- 강력한 비밀번호 사용
- 정기적인 비밀번호 변경

---

## 📝 유지보수

### 백업
```bash
# DB 백업 스크립트
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U admin biz_retriever > ./data/backups/db_$DATE.sql
```

### 업데이트
```bash
# 코드 업데이트
git pull origin master

# 재빌드 및 재시작
docker-compose up -d --build
```

---

**작성자**: AI Agent  
**최종 수정**: 2026-01-26  
**상태**: 4GB RAM 최적화 완료
