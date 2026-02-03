# 🚀 즉시 배포 가이드

**모든 준비 완료!** 이제 다음 명령어만 실행하면 됩니다.

---

## ✅ 완료된 사항

- ✅ Neon Postgres 연결 테스트 (PostgreSQL 17.7)
- ✅ Upstash Redis 연결 테스트 (Redis 8.2.0)
- ✅ JWT Secret 생성
- ✅ Cron Secret 생성
- ✅ 환경 변수 파일 생성 (`.env.vercel`)

---

## 🔥 배포 단계 (3단계)

### Step 1: Vercel 로그인 및 프로젝트 연결

```bash
# Vercel 로그인 (브라우저가 열립니다)
vercel login

# 프로젝트 연결
cd /c/sideproject
vercel link
```

**프롬프트가 나오면**:
- Set up and deploy? → **Yes**
- Which scope? → 본인 계정 선택
- Link to existing project? → **No** (새 프로젝트)
- Project name? → `biz-retriever` (엔터)
- In which directory? → `.` (엔터)

---

### Step 2: 환경 변수 설정 (자동)

```bash
# 자동 설정 스크립트 실행
chmod +x setup-vercel-credentials.sh
./setup-vercel-credentials.sh
```

**이 스크립트가 자동으로**:
- ✅ NEON_DATABASE_URL 설정 (production, preview, development)
- ✅ UPSTASH_REDIS_URL 설정 (production, preview, development)
- ✅ SECRET_KEY 설정 (production, preview, development)
- ✅ CRON_SECRET 설정 (production, preview, development)

**확인:**
```bash
vercel env ls
```

---

### Step 3: Preview 배포 (자동)

```bash
# Preview 자동 배포 + 검증
chmod +x scripts/deploy-preview.sh
./scripts/deploy-preview.sh
```

**이 스크립트가 자동으로**:
1. ✅ Vercel 로그인 상태 확인
2. ✅ 프로젝트 연결 확인
3. ✅ 환경 변수 4개 검증
4. ✅ Git 상태 확인
5. ✅ Preview 배포 실행
6. ✅ 배포 검증 (18개 자동 테스트)

**성공하면 다음과 같이 표시됩니다**:
```
🎉 배포 성공!
Preview URL: https://biz-retriever-xxx.vercel.app

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 배포 검증 시작
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏥 Health Check
  Health endpoint... ✅ PASS (HTTP 200)

📚 API Documentation
  Swagger UI... ✅ PASS (HTTP 200)
  OpenAPI JSON... ✅ PASS (HTTP 200)

🌐 Frontend Pages
  Login page... ✅ PASS (HTTP 200)
  Dashboard... ✅ PASS (HTTP 200)
  ...

📊 Summary
  Passed: 18
  Failed: 0
  Pass Rate: 100%

🎉 모든 테스트 통과!
```

---

## 🎯 배포 후 확인

### 1. 브라우저에서 테스트

```
https://your-preview-url.vercel.app
```

- 로그인 페이지 로드 확인
- 회원가입 테스트
- 로그인 테스트
- Dashboard 로딩 확인

### 2. API 테스트

```bash
# Health Check
curl https://your-preview-url.vercel.app/health

# API Docs
open https://your-preview-url.vercel.app/docs
```

### 3. 로그 확인

```bash
# 실시간 로그
vercel logs --follow

# 에러 로그만
vercel logs --follow | grep ERROR
```

---

## 🚀 프로덕션 배포

Preview 테스트가 모두 통과하면:

```bash
# feature 브랜치를 master로 병합
git checkout master
git merge feature/vercel-migration

# 프로덕션 배포
git push origin master

# Vercel이 자동으로 프로덕션 배포합니다!
```

**프로덕션 URL**: https://biz-retriever.vercel.app

---

## 🔧 문제 해결

### 문제 1: 로그인이 안 됨

```bash
# Vercel 재로그인
vercel logout
vercel login
```

### 문제 2: 환경 변수 설정 실패

```bash
# 수동으로 하나씩 설정
echo "postgresql://neondb_owner:npg_KWi4aONZ3dUY@ep-red-math-ahf683ld-pooler.c-3.us-east-1.aws.neon.tech/neondb" | vercel env add NEON_DATABASE_URL production

# 다른 변수들도 동일하게 (setup-vercel-credentials.sh 참고)
```

### 문제 3: 배포 실패

```bash
# 로그 확인
vercel logs

# 재배포
vercel --force
```

### 문제 4: 데이터베이스 연결 오류

**Neon 데이터베이스에 테이블이 없을 수 있습니다.**

Vercel 배포가 성공하면, 다음 명령으로 테이블 생성:

```bash
# 로컬에서 Neon에 직접 마이그레이션
export DATABASE_URL="postgresql+asyncpg://neondb_owner:npg_KWi4aONZ3dUY@ep-red-math-ahf683ld-pooler.c-3.us-east-1.aws.neon.tech/neondb"

python -m alembic upgrade head
```

또는 Vercel 함수에서 자동 실행:
- 첫 API 호출 시 자동으로 테이블 생성됨 (app/core/database.py의 init_db 함수)

---

## 📋 체크리스트

배포 전:
- [ ] `vercel login` 완료
- [ ] `vercel link` 완료
- [ ] `./setup-vercel-credentials.sh` 실행
- [ ] `vercel env ls`로 환경 변수 4개 확인

배포:
- [ ] `./scripts/deploy-preview.sh` 실행
- [ ] 18개 테스트 모두 통과
- [ ] Preview URL 브라우저에서 확인

프로덕션:
- [ ] Preview 수동 테스트 완료
- [ ] `git merge feature/vercel-migration`
- [ ] `git push origin master`
- [ ] 프로덕션 URL 확인

---

## 💡 팁

### 빠른 재배포
```bash
# 코드 수정 후 빠르게 재배포
vercel --prod  # 프로덕션 즉시 배포
vercel         # Preview 배포
```

### 환경별 배포
```bash
vercel --prod              # 프로덕션
vercel                     # Preview (현재 브랜치)
vercel --env=development   # Development
```

### 로그 모니터링
```bash
# Preview 로그
vercel logs

# Production 로그
vercel logs --prod

# 실시간 로그
vercel logs --follow
```

---

**지금 바로 시작하세요!** 🚀

```bash
# 1단계
vercel login

# 2단계
vercel link

# 3단계
./setup-vercel-credentials.sh

# 4단계
./scripts/deploy-preview.sh
```

**예상 소요 시간**: 10-15분

---

**문제가 발생하면**:
1. `vercel logs`로 에러 확인
2. `.env.vercel` 파일의 URL 확인
3. Neon/Upstash Console에서 서비스 상태 확인
4. GitHub Issues에 로그와 함께 문의

**성공하면 축하드립니다!** 🎉
