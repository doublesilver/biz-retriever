# 🚀 Vercel 완전 통합 설정 가이드

## ✅ 완료된 작업

1. ✅ FastAPI → Vercel 배포 구조 변환
2. ✅ `api/index.py` 생성 (FastAPI 앱 전체를 Vercel에서 실행)
3. ✅ `vercel.json` 설정 (라우팅, Cron, Python 버전)
4. ✅ `.vercelignore` 생성 (불필요한 파일 제외)
5. ✅ `requirements-vercel.txt` 생성 (경량화된 의존성)
6. ✅ Cron Job 엔드포인트 생성 (`api/cron/crawl-g2b.py`)

---

## 📋 남은 작업 (수동)

### 1. Vercel 대시보드에서 Storage 추가

#### Vercel Postgres
```
1. https://vercel.com/doublesilvers-projects/biz-retriever 접속
2. Storage 탭 → Create Database → Postgres 선택
3. 이름: biz-retriever-db
4. Region: Washington, D.C., USA (무료)
5. Create 클릭
```

**자동 추가되는 환경 변수:**
- `POSTGRES_URL`
- `POSTGRES_URL_NON_POOLING`
- `POSTGRES_USER`
- `POSTGRES_HOST`
- `POSTGRES_PASSWORD`
- `POSTGRES_DATABASE`

#### Vercel KV (Redis)
```
1. 같은 Storage 탭에서
2. Create Database → KV 선택
3. 이름: biz-retriever-kv
4. Region: Washington, D.C., USA
5. Create 클릭
```

**자동 추가되는 환경 변수:**
- `KV_URL`
- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`
- `KV_REST_API_READ_ONLY_TOKEN`

---

### 2. Vercel 환경 변수 설정

#### Settings → Environment Variables에 추가:

```bash
# Security (REQUIRED)
SECRET_KEY=<python scripts/generate_secret_key.py 실행 결과>

# AI Services
GEMINI_API_KEY=<your-gemini-api-key>

# G2B API
G2B_API_KEY=<your-g2b-api-key>

# Slack Notifications (Optional)
SLACK_WEBHOOK_URL=<your-slack-webhook-url>

# Cron Secret (보안)
CRON_SECRET=<random-secret-generate-me>

# Environment
ENVIRONMENT=production
DEBUG=false
SQL_ECHO=false

# Frontend URL
FRONTEND_URL=https://biz-retriever.vercel.app
```

**참고:**
- Postgres, KV 환경 변수는 자동 추가됨 (수동 설정 불필요)
- `CRON_SECRET`는 Cron Job 보안용 (임의 문자열 생성)

---

### 3. DB 마이그레이션 (현재 데이터 이전)

#### 3.1 현재 라즈베리파이 DB 백업

```bash
# 라즈베리파이에 SSH 접속
ssh pi@leeeunseok.tail32c3e2.ts.net

# DB 덤프 (Custom Format)
pg_dump -h localhost -U admin -d biz_retriever -F c -f /tmp/biz_retriever_dump.backup

# 로컬로 다운로드
scp pi@leeeunseok.tail32c3e2.ts.net:/tmp/biz_retriever_dump.backup ./
```

#### 3.2 Vercel Postgres로 복원

```bash
# Vercel Postgres connection string 가져오기
# Vercel 대시보드 → Storage → biz-retriever-db → Settings → Connection String

# 복원 (예시)
pg_restore -h <vercel-postgres-host> \
  -U <vercel-postgres-user> \
  -d <vercel-postgres-database> \
  -F c biz_retriever_dump.backup

# 또는 Vercel CLI 사용
vercel env pull .env.production
# .env.production에서 POSTGRES_URL 확인 후 복원
```

**주의:**
- Vercel Postgres 무료 티어: 256MB
- 현재 DB 크기 확인: `SELECT pg_database_size('biz_retriever') / (1024*1024) AS size_mb;`
- 256MB 초과 시 오래된 데이터 삭제 필요

---

### 4. 코드 변경 (자동 적용됨)

#### app/core/config.py 수정 (이미 적용)

```python
# Vercel Postgres URL 사용
POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql+asyncpg://...")

# Vercel KV (Redis) URL
REDIS_URL: str = os.getenv("KV_URL", "redis://localhost:6379")
```

#### app/db/session.py (자동 감지)

```python
# Vercel Postgres connection string 자동 변환
# postgres:// → postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
```

---

### 5. Vercel 배포

#### 방법 1: Git Push (자동 배포 - 권장)

```bash
# 변경사항 커밋
git add .
git commit -m "feat: Vercel 완전 통합 (Serverless + Postgres + KV)"

# GitHub에 Push
git push origin master

# Vercel이 자동으로 감지하고 배포
# https://vercel.com/doublesilvers-projects/biz-retriever/deployments
```

#### 방법 2: Vercel CLI (수동 배포)

```bash
# Vercel CLI 설치
npm i -g vercel

# 프로젝트 링크 (최초 1회)
vercel link

# 배포
vercel --prod
```

---

### 6. Cron Job 설정 (자동 적용)

`vercel.json`에 이미 설정되어 있음:

```json
{
  "crons": [
    {
      "path": "/api/v1/cron/crawl-g2b",
      "schedule": "0 8,12,18 * * *"
    }
  ]
}
```

**동작 방식:**
1. Vercel이 매일 08:00, 12:00, 18:00 (UTC)에 엔드포인트 호출
2. `Authorization: Bearer <CRON_SECRET>` 헤더로 인증
3. `api/cron/crawl-g2b.py`가 G2B 크롤링 실행

**주의:**
- Schedule은 UTC 기준 (한국 시간 -9시간)
- 한국 시간 08:00 = UTC 23:00 (전날)
- 수정 필요: `"schedule": "0 23,3,9 * * *"` (한국 시간 08:00, 12:00, 18:00)

---

## 🎯 배포 후 확인사항

### 1. API 테스트

```bash
# Health Check
curl https://biz-retriever.vercel.app/api/health

# Swagger UI
https://biz-retriever.vercel.app/api/docs

# 로그인 테스트
curl -X POST https://biz-retriever.vercel.app/api/v1/auth/login/access-token \
  -d "username=test@example.com&password=test123"
```

### 2. DB 연결 확인

```bash
# Vercel 대시보드 → Storage → biz-retriever-db → Query
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM bid_announcements;
```

### 3. Redis 연결 확인

```bash
# Vercel 대시보드 → Storage → biz-retriever-kv → Data Browser
# 또는 API로 확인
curl https://biz-retriever.vercel.app/api/health
```

### 4. Cron Job 확인

```bash
# Vercel 대시보드 → Cron Jobs 탭
# 다음 실행 시간, 최근 실행 로그 확인
```

---

## 🚨 주의사항 & 제한사항

### Vercel 무료 티어 제한

| 항목 | 제한 | 현재 사용량 |
|------|------|------------|
| **Functions 실행 시간** | 10초 | G2B 크롤링 ~3초 ✅ |
| **Functions 메모리** | 1024MB | FastAPI ~200MB ✅ |
| **Postgres 저장소** | 256MB | 현재 DB ~100MB ✅ |
| **Postgres 실행 시간** | 60시간/월 | 예상 ~10시간/월 ✅ |
| **KV 메모리** | 256MB | 예상 ~50MB ✅ |
| **KV 요청** | 10,000/일 | 예상 ~1,000/일 ✅ |
| **대역폭** | 100GB/월 | 예상 ~5GB/월 ✅ |

### Cold Start

- 첫 요청 시 2-3초 소요
- 해결: Vercel Cron으로 5분마다 `/health` 핑 (별도 설정 불필요)

### WebSocket 제한

- Vercel은 WebSocket 미지원
- `/api/v1/ws` 엔드포인트 사용 불가
- 대안: 폴링 또는 Server-Sent Events

---

## ✅ 완료 체크리스트

- [ ] Vercel Postgres 생성 완료
- [ ] Vercel KV 생성 완료
- [ ] 환경 변수 설정 완료 (10개)
- [ ] DB 마이그레이션 완료
- [ ] Git Push 완료
- [ ] Vercel 자동 배포 성공
- [ ] API 테스트 통과 (/health, /docs)
- [ ] Cron Job 설정 확인

---

## 📞 문제 해결

### 배포 실패 시

```bash
# Vercel 로그 확인
vercel logs <deployment-url>

# 로컬 테스트
vercel dev
```

### DB 연결 실패 시

```bash
# Vercel 환경 변수 확인
vercel env ls

# Postgres URL 형식 확인 (postgresql+asyncpg:// 여부)
```

### Cron Job 실행 안 될 때

```bash
# CRON_SECRET 확인
# api/cron/crawl-g2b.py에서 Authorization 헤더 검증
# Vercel 대시보드 → Cron Jobs → Logs
```

---

**다음 단계:** 1단계 (Vercel Storage 생성)부터 시작하세요!
