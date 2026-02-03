# 📝 Vercel 환경 변수 설정 템플릿

Vercel 대시보드 → Settings → Environment Variables에 추가하세요.

---

## ✅ 자동 추가되는 변수 (Storage 생성 시)

Vercel Postgres와 KV를 생성하면 자동으로 추가됩니다. **수동 설정 불필요**

### Vercel Postgres (자동)
```
POSTGRES_URL=postgres://default:xxxx@xxxx.postgres.vercel-storage.com:5432/verceldb
POSTGRES_URL_NON_POOLING=postgres://default:xxxx@xxxx.postgres.vercel-storage.com:5432/verceldb
POSTGRES_USER=default
POSTGRES_HOST=xxxx.postgres.vercel-storage.com
POSTGRES_PASSWORD=xxxx
POSTGRES_DATABASE=verceldb
```

### Vercel KV (자동)
```
KV_URL=redis://default:xxxx@xxxx.kv.vercel-storage.com:6379
KV_REST_API_URL=https://xxxx.kv.vercel-storage.com
KV_REST_API_TOKEN=xxxx
KV_REST_API_READ_ONLY_TOKEN=xxxx
```

---

## 🔑 수동 설정 필요한 변수

아래 변수들을 **수동으로** 추가하세요:

### 1. Security (필수)

```bash
# SECRET_KEY 생성 방법:
# python scripts/generate_secret_key.py
SECRET_KEY=your-super-secret-key-minimum-32-characters-long

# Cron Job 보안용 (임의 문자열)
# python -c "import secrets; print(secrets.token_urlsafe(32))"
CRON_SECRET=your-random-cron-secret-key
```

---

### 2. AI Services (필수)

```bash
# Google Gemini API Key
# https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

### 3. G2B API (필수)

```bash
# 나라장터 공공데이터 API Key
# https://www.data.go.kr (회원가입 후 API 신청)
G2B_API_KEY=your-g2b-api-key-from-data-go-kr
```

---

### 4. Slack Notifications (선택)

```bash
# Slack Webhook URL (알림 받으려면 설정)
# https://api.slack.com/messaging/webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX

# Slack Channel (기본값: #입찰-알림)
SLACK_CHANNEL=#입찰-알림
```

---

### 5. Environment (선택)

```bash
# Production 환경 설정
ENVIRONMENT=production
DEBUG=false
SQL_ECHO=false

# Frontend URL
FRONTEND_URL=https://biz-retriever.vercel.app
```

---

### 6. Payment Gateway (Phase 3 - 선택)

```bash
# Tosspayments (구독 결제용)
# https://developers.tosspayments.com/
TOSSPAYMENTS_SECRET_KEY=
TOSSPAYMENTS_CLIENT_KEY=
```

---

### 7. Email Notifications (Phase 8 - 선택)

```bash
# SendGrid (이메일 알림용)
# https://sendgrid.com/
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@biz-retriever.com
SENDGRID_FROM_NAME=Biz-Retriever
```

---

## 🎯 환경 변수 추가 방법

### 방법 1: Vercel 대시보드 (권장)

1. https://vercel.com/doublesilvers-projects/biz-retriever 접속
2. **Settings** 탭 클릭
3. **Environment Variables** 선택
4. 변수 추가:
   - **Key**: 변수 이름 (예: `SECRET_KEY`)
   - **Value**: 변수 값 (예: `your-secret-key`)
   - **Environment**: Production, Preview, Development 선택
5. **Save** 클릭

**팁:** Production, Preview, Development 모두 체크하세요!

---

### 방법 2: Vercel CLI

```bash
# 환경 변수 추가
vercel env add SECRET_KEY

# 환경 변수 목록 확인
vercel env ls

# 로컬에 환경 변수 다운로드
vercel env pull .env.production
```

---

## ✅ 설정 완료 체크리스트

필수 변수 (7개):
- [ ] `SECRET_KEY` (보안)
- [ ] `CRON_SECRET` (Cron Job 보안)
- [ ] `GEMINI_API_KEY` (AI 분석)
- [ ] `G2B_API_KEY` (공고 크롤링)
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `FRONTEND_URL=https://biz-retriever.vercel.app`

선택 변수:
- [ ] `SLACK_WEBHOOK_URL` (Slack 알림)
- [ ] `TOSSPAYMENTS_SECRET_KEY` (결제 - Phase 3)
- [ ] `SENDGRID_API_KEY` (이메일 - Phase 8)

자동 생성 (10개):
- [ ] `POSTGRES_URL` (Vercel Postgres 생성 시)
- [ ] `KV_URL` (Vercel KV 생성 시)
- [ ] ... (나머지 8개)

---

## 🔧 문제 해결

### SECRET_KEY 생성

```bash
# 방법 1: Python 스크립트
python scripts/generate_secret_key.py

# 방법 2: 직접 생성
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### CRON_SECRET 생성

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 환경 변수 확인

```bash
# Vercel CLI로 확인
vercel env ls

# 또는 대시보드에서 확인
# https://vercel.com/doublesilvers-projects/biz-retriever/settings/environment-variables
```

---

**다음 단계:** 모든 환경 변수 설정 후 Vercel에 배포하세요!
