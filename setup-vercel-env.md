# Vercel 환경 변수 설정 가이드

## 🚀 Wave 5: Deployment 시작!

이 가이드는 Neon Postgres와 Upstash Redis를 Vercel에 연결하는 방법을 안내합니다.

---

## Step 1: Vercel CLI 로그인

```bash
cd /c/sideproject
vercel login
```

브라우저가 열리면 로그인하세요.

---

## Step 2: Vercel 프로젝트 연결

```bash
# 기존 프로젝트가 있다면 연결
vercel link

# 새 프로젝트라면 생성
vercel
```

---

## Step 3: 환경 변수 설정

### 필수 환경 변수

다음 명령어를 실행하여 환경 변수를 설정하세요. **실제 값으로 교체하세요!**

```bash
# 1. Neon Postgres (가장 중요!)
vercel env add NEON_DATABASE_URL production
# 입력 프롬프트가 나오면 Neon 연결 문자열을 붙여넣기:
# postgresql://user:password@ep-xxx-xxx.neon.tech/database?pgbouncer=true

# Preview와 Development 환경에도 동일하게 추가
vercel env add NEON_DATABASE_URL preview
vercel env add NEON_DATABASE_URL development

# 2. Upstash Redis
vercel env add UPSTASH_REDIS_URL production
# redis://default:password@us1-xxx-xxx.upstash.io:6379

vercel env add UPSTASH_REDIS_URL preview
vercel env add UPSTASH_REDIS_URL development

# 3. JWT Secret Key (새로 생성)
# 먼저 로컬에서 생성:
openssl rand -hex 32
# 출력된 값을 복사하여 입력

vercel env add SECRET_KEY production
vercel env add SECRET_KEY preview
vercel env add SECRET_KEY development

# 4. Cron Job Secret (새로 생성)
openssl rand -hex 32

vercel env add CRON_SECRET production
vercel env add CRON_SECRET preview
vercel env add CRON_SECRET development
```

### 권장 환경 변수 (선택사항)

```bash
# Google Gemini API (AI 분석 기능)
vercel env add GEMINI_API_KEY production
vercel env add GEMINI_API_KEY preview

# G2B API (나라장터 크롤링)
vercel env add G2B_API_KEY production
vercel env add G2B_API_KEY preview

# Slack Webhook (알림)
vercel env add SLACK_WEBHOOK_URL production
vercel env add SLACK_WEBHOOK_URL preview
```

---

## Step 4: 환경 변수 확인

```bash
# 설정된 환경 변수 목록 확인 (값은 숨겨짐)
vercel env ls

# 로컬에 .env.local 파일로 다운로드 (테스트용)
vercel env pull .env.vercel
```

---

## Step 5: 데이터베이스 마이그레이션

Neon Postgres에 스키마를 생성해야 합니다.

### Option A: Alembic 마이그레이션 (권장)

```bash
# Neon 연결 문자열을 환경 변수로 설정
export DATABASE_URL="postgresql://user:password@ep-xxx-xxx.neon.tech/database?pgbouncer=true"

# 마이그레이션 실행
alembic upgrade head
```

### Option B: 수동 SQL 실행

Neon Console에서 직접 SQL을 실행:
1. [Neon Console](https://console.neon.tech) 로그인
2. SQL Editor 열기
3. `app/models/` 폴더의 모델을 참고하여 CREATE TABLE 실행

---

## Step 6: Preview 배포 테스트

```bash
# 현재 브랜치를 Preview 환경으로 배포
vercel

# 또는 특정 브랜치 배포
git push origin feature/vercel-migration
# Vercel이 자동으로 감지하여 배포
```

배포 완료 후 다음을 확인:
- Health Check: `https://your-preview-url.vercel.app/health`
- API Docs: `https://your-preview-url.vercel.app/docs`
- Frontend: `https://your-preview-url.vercel.app/`

---

## Step 7: 프로덕션 배포

모든 테스트가 통과하면 main 브랜치로 병합:

```bash
# feature 브랜치에서 main으로 병합
git checkout master
git merge feature/vercel-migration
git push origin master

# Vercel이 자동으로 프로덕션 배포
```

---

## 🔍 Troubleshooting

### Database Connection Error

```bash
# 연결 테스트 (로컬)
psql "postgresql://user:password@ep-xxx-xxx.neon.tech/database?pgbouncer=true"

# Vercel 로그 확인
vercel logs --follow
```

### Redis Connection Error

```bash
# 연결 테스트 (로컬)
redis-cli -u "redis://default:password@us1-xxx-xxx.upstash.io:6379"

# PING 명령으로 응답 확인
```

### Environment Variable Not Found

```bash
# 환경 변수 다시 설정
vercel env rm NEON_DATABASE_URL production
vercel env add NEON_DATABASE_URL production

# 프로젝트 재배포
vercel --prod
```

---

## 📋 체크리스트

마이그레이션 완료 전 확인사항:

- [ ] Vercel CLI 로그인 완료
- [ ] Vercel 프로젝트 연결 완료
- [ ] NEON_DATABASE_URL 설정 (production, preview, development)
- [ ] UPSTASH_REDIS_URL 설정 (production, preview, development)
- [ ] SECRET_KEY 설정 (모든 환경)
- [ ] CRON_SECRET 설정 (모든 환경)
- [ ] GEMINI_API_KEY 설정 (선택)
- [ ] G2B_API_KEY 설정 (선택)
- [ ] Neon 데이터베이스 스키마 생성 완료
- [ ] Preview 배포 테스트 완료
- [ ] Health Check API 응답 확인
- [ ] Frontend 페이지 로드 확인
- [ ] 로그인/회원가입 동작 확인
- [ ] 프로덕션 배포 완료

---

## 📚 참고 문서

- [VERCEL_ENV_VARS.md](./docs/VERCEL_ENV_VARS.md) - 전체 환경 변수 목록
- [VERCEL_DEPLOYMENT_FINAL.md](./docs/VERCEL_DEPLOYMENT_FINAL.md) - 배포 상세 가이드
- [Neon Documentation](https://neon.tech/docs)
- [Upstash Documentation](https://upstash.com/docs)

---

**다음 단계**: 위 가이드를 따라 환경 변수를 설정한 후 Preview 배포를 진행하세요!
