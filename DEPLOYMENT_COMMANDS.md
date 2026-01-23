# 🚀 Production 배포 명령어 가이드

## 1단계: Docker 상태 확인

```powershell
# Docker 버전 확인
docker --version

# Docker 실행 확인
docker ps

# Docker Compose 버전 확인
docker-compose --version
```

---

## 2단계: Docker 서비스 시작

```powershell
# PostgreSQL과 Redis만 먼저 시작
docker-compose up -d db redis

# 컨테이너 상태 확인 (30초 정도 대기 후)
docker-compose ps

# 로그 확인 (문제 발생 시)
docker-compose logs db
docker-compose logs redis
```

---

## 3단계: 데이터베이스 마이그레이션

```powershell
# 가상환경 활성화 (이미 되어있다면 생략)
# venv\Scripts\activate

# Alembic 설치 확인
pip install alembic

# 마이그레이션 실행
alembic upgrade head

# 마이그레이션 확인
alembic current
```

---

## 4단계: 초기 사용자 생성 (선택)

```powershell
# Python 스크립트로 사용자 생성
python -c "
from app.core.security import get_password_hash
print('Password hash:', get_password_hash('admin123'))
"

# 또는 API로 회원가입 (서버 실행 후)
# POST http://localhost:8000/api/v1/auth/register
```

---

## 5단계: 애플리케이션 서버 실행

### Option A: 직접 실행 (개발용)
```powershell
# 메인 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B: Docker Compose로 전체 실행 (권장)
```powershell
# 모든 서비스 시작 (app, celery worker, celery beat 포함)
docker-compose up -d

# 전체 로그 확인
docker-compose logs -f

# 특정 서비스만 로그 확인
docker-compose logs -f app
```

---

## 6단계: Celery Worker 실행 (별도 터미널)

```powershell
# Celery Worker 시작
celery -A app.worker.celery_app worker --loglevel=info --pool=solo

# Windows에서 --pool=solo 옵션 필수!
```

---

## 7단계: Celery Beat 실행 (별도 터미널)

```powershell
# Celery Beat 시작 (스케줄러)
celery -A app.worker.celery_app beat --loglevel=info
```

---

## 8단계: 애플리케이션 접속

```powershell
# 브라우저에서 접속
start http://localhost:8000

# API 문서 확인
start http://localhost:8000/docs

# Health Check
curl http://localhost:8000/health
```

---

## 9단계: 크롤링 테스트

```powershell
# 수동 크롤링 트리거 (로그인 필요)
# 1. 먼저 로그인하여 토큰 받기
$body = @{
    username = "test@example.com"
    password = "password123"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login/access-token" -Method Post -Body "username=test@example.com&password=password123" -ContentType "application/x-www-form-urlencoded"
$token = $response.access_token

# 2. 크롤링 실행
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/crawler/trigger" -Method Post -Headers @{Authorization="Bearer $token"}
```

---

## 10단계: ML 모델 학습 (데이터 수집 후)

```powershell
# Python 스크립트로 모델 학습
python -c "
import asyncio
from app.services.ml_service import ml_service
from app.db.session import SessionLocal

async def train():
    async with SessionLocal() as db:
        result = await ml_service.train_model(db)
        print('Training result:', result)

asyncio.run(train())
"
```

---

## 트러블슈팅

### Docker 연결 실패 시
```powershell
# WSL 재시작
wsl --shutdown

# Docker Desktop 재시작
Stop-Process -Name "Docker Desktop" -Force
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# 1분 대기 후 재시도
Start-Sleep -Seconds 60
docker ps
```

### 포트 충돌 시
```powershell
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# 프로세스 종료 (PID 확인 후)
taskkill /F /PID <PID>
```

### 데이터베이스 초기화 (주의!)
```powershell
# 모든 데이터 삭제 후 재시작
docker-compose down -v
docker-compose up -d db redis
alembic upgrade head
```

---

## 서비스 중지

```powershell
# 모든 Docker 서비스 중지
docker-compose down

# 볼륨까지 삭제 (데이터 삭제됨!)
docker-compose down -v

# Celery Worker/Beat 중지 (Ctrl+C)
```

---

## 빠른 시작 (All-in-One)

```powershell
# 1. Docker 서비스 시작
docker-compose up -d

# 2. 마이그레이션
alembic upgrade head

# 3. 브라우저 열기
start http://localhost:8000

# 완료! 🎉
```

---

## 현재 Mock Server 사용 중이라면

```powershell
# Mock Server 프로세스 종료
# Ctrl+C로 터미널에서 종료

# 또는 포트로 찾아서 종료
$processes = netstat -ano | findstr :8004
# PID 확인 후
taskkill /F /PID <PID>
```
