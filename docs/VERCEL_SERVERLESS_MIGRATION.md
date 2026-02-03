# 🚀 Vercel Serverless 마이그레이션 가이드

## 목표

**라즈베리파이 (FastAPI + PostgreSQL + Redis)** → **Vercel 완전 통합**

---

## ✅ 1단계: Vercel 프로젝트 설정 (수동 작업 - 지금 하세요!)

### 1.1 Vercel Postgres 추가

```bash
# Vercel 대시보드 접속
https://vercel.com/doublesilvers-projects/biz-retriever

# Storage 탭 클릭
# "Create Database" → "Postgres" 선택
# 이름: biz-retriever-db
# Region: Washington, D.C., USA (무료 티어)
# Create 클릭

# 완료 후 connection string 복사:
# postgres://default:xxxx@xxxx.postgres.vercel-storage.com:5432/verceldb
```

**무료 티어:**
- 256MB 스토리지
- 60시간 컴퓨팅 시간/월
- 충분한 용량 (현재 DB 100MB 추정)

---

### 1.2 Vercel KV (Redis) 추가

```bash
# Vercel 대시보드 → Storage 탭
# "Create Database" → "KV" 선택
# 이름: biz-retriever-kv
# Region: Washington, D.C., USA
# Create 클릭

# 완료 후 환경 변수 자동 추가됨:
# KV_URL=redis://default:xxxx@xxxx.kv.vercel-storage.com:6379
# KV_REST_API_URL=https://xxxx.kv.vercel-storage.com
# KV_REST_API_TOKEN=xxxx
```

**무료 티어:**
- 256MB 메모리
- 10,000 명령/일
- 충분한 용량 (현재 Redis 사용량 < 50MB)

---

## ✅ 2단계: FastAPI → Vercel Serverless Functions 변환

### 2.1 디렉토리 구조 변경

```
# 기존
app/
  api/
    endpoints/
      auth.py
      bids.py
      ...

# 새로운 (Vercel Functions)
api/
  auth/
    login.py
    register.py
  bids/
    list.py
    create.py
  ...
```

### 2.2 Function 예시

**기존 FastAPI 엔드포인트:**
```python
# app/api/endpoints/auth.py
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    ...
```

**새로운 Vercel Function:**
```python
# api/auth/login.py
from fastapi import Request
from fastapi.responses import JSONResponse

async def handler(request: Request):
    body = await request.json()
    # 로그인 로직
    return JSONResponse({"access_token": token})
```

---

## ✅ 3단계: DB 마이그레이션

### 3.1 현재 DB 덤프

```bash
# 라즈베리파이에서 실행
pg_dump -h localhost -U admin -d biz_retriever -F c -f dump.backup

# 로컬로 다운로드
scp pi@raspberrypi:/path/dump.backup ./
```

### 3.2 Vercel Postgres로 복원

```bash
# Vercel Postgres connection string 사용
pg_restore -h xxxx.postgres.vercel-storage.com -U default -d verceldb -F c dump.backup
```

---

## ✅ 4단계: Redis → Vercel KV 전환

### 4.1 코드 변경

**기존 Redis:**
```python
import redis
r = redis.Redis(host='localhost', port=6379)
r.set('key', 'value')
```

**새로운 Vercel KV:**
```python
from vercel_kv import VercelKV
kv = VercelKV.from_env()
await kv.set('key', 'value')
```

---

## ✅ 5단계: Taskiq → Vercel Cron Jobs

### 5.1 크론 작업 설정

**기존 Taskiq:**
```python
# app/worker/taskiq_app.py
@scheduler.task(cron="0 8,12,18 * * *")
async def crawl_g2b():
    ...
```

**새로운 Vercel Cron (vercel.json):**
```json
{
  "crons": [
    {
      "path": "/api/cron/crawl-g2b",
      "schedule": "0 8,12,18 * * *"
    }
  ]
}
```

**Cron Function:**
```python
# api/cron/crawl-g2b.py
from fastapi import Request, Response

async def handler(request: Request):
    # Authorization 검증 (Vercel Cron secret)
    if request.headers.get("Authorization") != f"Bearer {CRON_SECRET}":
        return Response(status_code=401)
    
    # 크롤링 로직
    await crawl_g2b_announcements()
    return Response(status_code=200)
```

---

## ✅ 6단계: 환경 변수 설정

```bash
# Vercel 대시보드 → Settings → Environment Variables

# 기존 .env에서 복사
GEMINI_API_KEY=your-key
G2B_API_KEY=your-key
SLACK_WEBHOOK_URL=your-url
SECRET_KEY=your-secret

# Vercel가 자동 추가한 것
POSTGRES_URL=postgres://...
KV_URL=redis://...
```

---

## ✅ 7단계: vercel.json 설정

```json
{
  "buildCommand": "pip install -r requirements.txt",
  "devCommand": "uvicorn app.main:app --host 0.0.0.0 --port 3000",
  "installCommand": "pip install -r requirements.txt",
  "framework": null,
  "outputDirectory": "public",
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.11"
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/frontend/$1" }
  ],
  "crons": [
    {
      "path": "/api/cron/crawl-g2b",
      "schedule": "0 8,12,18 * * *"
    },
    {
      "path": "/api/cron/morning-briefing",
      "schedule": "30 8 * * *"
    }
  ]
}
```

---

## ✅ 8단계: 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 배포
vercel --prod

# 자동 배포 설정 (GitHub 연동)
# Vercel 대시보드 → Git → Connect Repository
```

---

## 📊 무료 티어 제한 확인

| 서비스 | 무료 티어 | 현재 사용량 | 여유 |
|--------|-----------|-------------|------|
| **Vercel Functions** | 100만 요청/월 | ~3,000 요청/월 | ✅ 99.7% |
| **Vercel Postgres** | 256MB, 60시간/월 | ~100MB, ~10시간/월 | ✅ 61% DB, 83% 시간 |
| **Vercel KV** | 256MB, 10K 명령/일 | ~50MB, ~1K 명령/일 | ✅ 80% 메모리, 90% 명령 |
| **Vercel 대역폭** | 100GB/월 | ~5GB/월 | ✅ 95% |

**결론: 무료 티어로 충분합니다!** 🎉

---

## 🎯 예상 작업 시간

| 단계 | 시간 |
|------|------|
| 1. Vercel 프로젝트 설정 | 10분 |
| 2. FastAPI → Functions 변환 | 2시간 |
| 3. DB 마이그레이션 | 30분 |
| 4. Redis → KV 전환 | 1시간 |
| 5. 환경 변수 설정 | 10분 |
| 6. Cron Jobs 설정 | 30분 |
| 7. 테스트 및 디버깅 | 1시간 |
| 8. 배포 및 검증 | 30분 |
| **총합** | **~6시간** |

---

## 🚨 주의사항

1. **DB 덤프 전 백업**: 라즈베리파이 DB를 백업하세요
2. **환경 변수 검증**: Vercel 대시보드에서 모든 환경 변수 확인
3. **Cold Start**: 첫 요청은 2-3초 걸림 (Vercel Cron으로 5분마다 핑)
4. **10초 제한**: Vercel Functions는 최대 10초 실행 (크롤링 최적화 필요)

---

## 📞 도움 필요 시

- Vercel Docs: https://vercel.com/docs
- Vercel Postgres: https://vercel.com/docs/storage/vercel-postgres
- Vercel KV: https://vercel.com/docs/storage/vercel-kv
- Vercel Cron Jobs: https://vercel.com/docs/cron-jobs

---

**다음 단계:** 1단계 완료 후 알려주세요!
