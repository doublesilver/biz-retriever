# 🚀 Vercel 완전 통합 배포 - 최종 가이드

## 📝 개요

**라즈베리파이 FastAPI 서버 → Vercel 완전 통합**

### 변경사항 요약

| Before (라즈베리파이) | After (Vercel) |
|----------------------|----------------|
| PostgreSQL (로컬) | Vercel Postgres (클라우드) |
| Redis (로컬) | Vercel KV (클라우드) |
| Taskiq Scheduler | Vercel Cron Jobs |
| 전기료 월 5천원 | 월 0원 (무료 티어) |
| 24시간 서버 관리 | 0시간 (자동 관리) |
| 라즈베리파이 레이턴시 20ms | Vercel 레이턴시 30-50ms (국내) |

---

## ✅ 준비 완료된 항목

1. ✅ `api/index.py` - FastAPI 앱 Vercel 엔트리 포인트
2. ✅ `vercel.json` - 라우팅, Cron, Python 설정
3. ✅ `.vercelignore` - 불필요한 파일 제외
4. ✅ `requirements-vercel.txt` - 경량화된 의존성
5. ✅ `api/cron/crawl-g2b.py` - G2B 크롤링 Cron Job
6. ✅ `app/core/config.py` - Vercel 환경 변수 지원

---

## 🎯 배포 순서 (따라하기)

### 1단계: Vercel Storage 생성 (10분)

#### 1.1 Vercel Postgres

```
1. https://vercel.com/doublesilvers-projects/biz-retriever 접속
2. Storage 탭 클릭
3. Create Database → Postgres 선택
4. 이름: biz-retriever-db
5. Region: Washington, D.C., USA (무료)
6. Create 클릭
```

**자동 생성되는 환경 변수 확인:**
- Settings → Environment Variables에서 `POSTGRES_URL` 확인

#### 1.2 Vercel KV (Redis)

```
1. 같은 Storage 탭
2. Create Database → KV 선택
3. 이름: biz-retriever-kv
4. Region: Washington, D.C., USA
5. Create 클릭
```

**자동 생성되는 환경 변수 확인:**
- `KV_URL` 확인

---

### 2단계: 환경 변수 설정 (5분)

Settings → Environment Variables에 **수동으로** 추가:

```bash
# 1. Security (필수)
SECRET_KEY=<python scripts/generate_secret_key.py 결과>
CRON_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(32))" 결과>

# 2. AI & API (필수)
GEMINI_API_KEY=<your-gemini-api-key>
G2B_API_KEY=<your-g2b-api-key>

# 3. Environment (필수)
ENVIRONMENT=production
DEBUG=false
SQL_ECHO=false
FRONTEND_URL=https://biz-retriever.vercel.app

# 4. Slack (선택)
SLACK_WEBHOOK_URL=<your-slack-webhook-url>
SLACK_CHANNEL=#입찰-알림
```

**팁:** Production, Preview, Development 모두 체크!

---

### 3단계: DB 마이그레이션 (20분)

#### 3.1 현재 DB 백업

```bash
# 라즈베리파이 SSH 접속
ssh pi@leeeunseok.tail32c3e2.ts.net

# DB 덤프
docker exec -it <postgres-container-id> pg_dump -U admin -d biz_retriever -F c -f /tmp/dump.backup

# 로컬로 다운로드
docker cp <postgres-container-id>:/tmp/dump.backup ./biz_retriever_dump.backup
scp pi@leeeunseok.tail32c3e2.ts.net:~/biz_retriever_dump.backup ./
```

#### 3.2 Vercel Postgres로 복원

```bash
# Vercel CLI로 connection string 확인
vercel env pull .env.production
# .env.production에서 POSTGRES_URL 확인

# 복원 (예시)
pg_restore -h <host> -U <user> -d <database> -F c biz_retriever_dump.backup

# 예: postgres://default:xxxx@ep-xxxx.us-east-1.postgres.vercel-storage.com:5432/verceldb
```

**또는 Vercel SQL Editor 사용:**
1. Storage → biz-retriever-db → Query
2. SQL 파일을 직접 붙여넣기

---

### 4단계: Git Push & 배포 (5분)

#### 4.1 변경사항 커밋

```bash
git status

# 현재 변경사항 확인
# - api/index.py
# - vercel.json
# - .vercelignore
# - requirements-vercel.txt
# - api/cron/crawl-g2b.py
# - app/core/config.py
# - docs/*.md

git add .
git commit -m "feat: Vercel 완전 통합 (Serverless + Postgres + KV + Cron)

- FastAPI 앱 Vercel 배포 구조 전환
- Vercel Postgres & KV 지원
- Vercel Cron Jobs로 스케줄링
- 환경 변수 자동 감지
- 라즈베리파이 대비 관리 부담 제로
"

git push origin master
```

#### 4.2 Vercel 자동 배포 확인

```
1. https://vercel.com/doublesilvers-projects/biz-retriever/deployments
2. 최신 배포 상태 확인 (Building → Ready)
3. 빌드 로그에서 에러 확인
```

---

### 5단계: 배포 검증 (10분)

#### 5.1 Health Check

```bash
curl https://biz-retriever.vercel.app/api/health

# 예상 응답:
# {"status":"ok","service":"Biz-Retriever","version":"1.0.0"}
```

#### 5.2 Swagger UI

```
https://biz-retriever.vercel.app/api/docs

# 모든 엔드포인트 목록 확인
# /api/v1/auth/login/access-token
# /api/v1/bids/
# /api/v1/analytics/summary
# ...
```

#### 5.3 로그인 테스트

```bash
# 테스트 계정으로 로그인
curl -X POST "https://biz-retriever.vercel.app/api/v1/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"

# 예상 응답:
# {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer"}
```

#### 5.4 DB 연결 확인

```bash
# Vercel 대시보드 → Storage → biz-retriever-db → Query
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM bid_announcements;

# 또는 API로 확인
curl "https://biz-retriever.vercel.app/api/v1/bids/" \
  -H "Authorization: Bearer <access-token>"
```

#### 5.5 Cron Job 확인

```
1. Vercel 대시보드 → Cron Jobs 탭
2. 다음 실행 시간 확인
3. 최근 실행 로그 확인 (08:00, 12:00, 18:00 UTC)

# 수동 트리거 (테스트)
curl -X POST "https://biz-retriever.vercel.app/api/v1/cron/crawl-g2b" \
  -H "Authorization: Bearer <CRON_SECRET>"
```

---

## 🚨 문제 해결

### 문제 1: 배포 실패 (Build Error)

**증상:**
```
Error: Could not install dependencies
```

**해결:**
1. `requirements-vercel.txt` 확인
2. Vercel 대시보드 → Settings → General → Python Version: 3.11 확인
3. 빌드 로그에서 구체적인 에러 확인

```bash
vercel logs <deployment-url>
```

---

### 문제 2: DB 연결 실패

**증상:**
```
Error: could not connect to server
```

**해결:**
1. Vercel 환경 변수 `POSTGRES_URL` 확인
2. app/core/config.py에서 URL 변환 로직 확인

```python
# postgres:// → postgresql+asyncpg://
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
```

3. Vercel SQL Editor로 직접 접속 테스트

---

### 문제 3: Cron Job 실행 안 됨

**증상:**
- Vercel Cron Jobs 탭에 기록 없음

**해결:**
1. `vercel.json`에서 Cron 설정 확인
2. `CRON_SECRET` 환경 변수 확인
3. `api/cron/crawl-g2b.py`에서 Authorization 검증 로직 확인

```bash
# 수동 테스트
curl -X POST "https://biz-retriever.vercel.app/api/v1/cron/crawl-g2b" \
  -H "Authorization: Bearer <CRON_SECRET>" \
  -v

# 401 Unauthorized → CRON_SECRET 불일치
# 200 OK → 정상 작동
```

---

### 문제 4: API 응답 느림 (Cold Start)

**증상:**
- 첫 요청 시 3-5초 소요

**해결:**
- 정상 동작 (Serverless Functions의 특성)
- Vercel Cron으로 5분마다 `/health` 핑 (별도 설정 불필요)

**추가 Cron (선택):**
```json
{
  "crons": [
    {
      "path": "/api/health",
      "schedule": "*/5 * * * *"
    }
  ]
}
```

---

## 📊 무료 티어 모니터링

### Vercel 대시보드에서 확인

```
1. Usage 탭
2. Functions: 실행 시간, 메모리 사용량
3. Storage: Postgres & KV 사용량
4. Bandwidth: 대역폭 사용량
```

### 제한 초과 시

| 리소스 | 무료 티어 | 초과 시 조치 |
|--------|-----------|--------------|
| Postgres (256MB) | 100MB 사용 중 | 오래된 공고 삭제 |
| KV (256MB) | 50MB 사용 중 | 캐시 TTL 단축 |
| Functions (100GB/월) | 5GB 사용 중 | 정상 |

---

## ✅ 완료 체크리스트

배포 전:
- [ ] Vercel Postgres 생성 완료
- [ ] Vercel KV 생성 완료
- [ ] 환경 변수 10개 설정 완료
- [ ] DB 백업 완료

배포 후:
- [ ] Git Push 완료
- [ ] Vercel 자동 배포 성공 (Ready)
- [ ] `/api/health` 응답 OK
- [ ] `/api/docs` Swagger UI 접속
- [ ] 로그인 테스트 성공
- [ ] DB 쿼리 성공
- [ ] Cron Job 설정 확인

---

## 🎉 배포 완료!

### 접속 URL

- **Frontend**: https://biz-retriever.vercel.app
- **Backend API**: https://biz-retriever.vercel.app/api
- **Swagger UI**: https://biz-retriever.vercel.app/api/docs
- **Health Check**: https://biz-retriever.vercel.app/api/health

### 라즈베리파이 종료

배포가 성공적으로 완료되면:

```bash
# 라즈베리파이 Docker 컨테이너 중지
ssh pi@leeeunseok.tail32c3e2.ts.net
docker-compose down

# 전원 종료 (선택)
sudo shutdown -h now
```

**축하합니다! 이제 서버 관리 부담 0으로 24시간 서비스를 운영할 수 있습니다!** 🚀
