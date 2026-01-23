# 🚀 Biz-Retriever 프로덕션 배포 가이드

## 📋 배포 전 체크리스트

### 필수 항목
- [ ] G2B API 키 발급
- [ ] Slack Webhook URL 설정
- [ ] OpenAI API 키 발급
- [ ] 강력한 SECRET_KEY 생성
- [ ] 데이터베이스 비밀번호 변경
- [ ] Redis 비밀번호 설정
- [ ] 프로덕션 도메인 설정
- [ ] CORS 설정 업데이트

### 권장 항목
- [ ] SSL/TLS 인증서 설정
- [ ] 로그 모니터링 구성
- [ ] 백업 전략 수립
- [ ] CI/CD 파이프라인 검증

---

## 🔑 1. G2B API 키 발급 (나라장터 공공데이터)

### 발급 절차

#### Step 1: 공공데이터포털 회원가입
1. [공공데이터포털](https://www.data.go.kr/) 접속
2. 회원가입 (개인 또는 기업)
3. 이메일 인증 완료

#### Step 2: API 활용 신청
1. 로그인 후 검색창에 **"입찰공고"** 검색
2. **"조달청_입찰공고 목록조회 서비스"** 선택
3. "활용신청" 버튼 클릭
4. 신청 정보 입력:
   ```
   활용 목적: 입찰 공고 자동 수집 및 분석 시스템 개발
   활용 분야: 정보통신
   상세 내용: 중소기업 대상 입찰 정보 큐레이션 서비스
   ```
5. 신청 완료 (즉시 승인 또는 1~2일 소요)

#### Step 3: API 키 확인
1. "마이페이지" → "오픈API" → "개발계정 상세"
2. **인증키(Encoding)** 복사
3. `.env` 파일에 입력:
   ```bash
   G2B_API_KEY=your_actual_g2b_api_key_here
   ```

#### 테스트
```bash
# API 키 테스트 스크립트
python scripts/test_g2b_api.py
```

### 발급 소요 시간
- 즉시 ~ 최대 2영업일

### 비용
- **무료** (일일 트래픽 제한: 10,000건)

---

## 📢 2. Slack Webhook URL 설정

### 발급 절차

#### Step 1: Slack Workspace 준비
1. Slack Workspace 생성 또는 기존 Workspace 사용
2. 알림을 받을 채널 생성 (예: `#입찰-알림`, `#biz-retriever`)

#### Step 2: Incoming Webhooks 앱 설치
1. Slack 좌측 하단 **"Apps"** 클릭
2. 검색창에 **"Incoming Webhooks"** 입력
3. "Add to Slack" 버튼 클릭
4. 채널 선택 (예: `#입찰-알림`)
5. "Add Incoming WebHooks integration" 클릭

#### Step 3: Webhook URL 복사
1. **Webhook URL** 형식 예시:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```
2. `.env` 파일에 입력:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   SLACK_CHANNEL=#입찰-알림
   ```

#### 테스트
```bash
# Webhook 테스트
python scripts/test_slack_notification.py
```

### 발급 소요 시간
- 즉시

### 비용
- **무료** (Slack Free Plan 사용 가능)

---

## 🤖 3. OpenAI API 키 발급

### 발급 절차

#### Step 1: OpenAI 계정 생성
1. [OpenAI Platform](https://platform.openai.com/) 접속
2. "Sign up" 또는 Google/Microsoft 계정으로 가입
3. 전화번호 인증 완료

#### Step 2: 결제 정보 등록
1. "Settings" → "Billing" 메뉴
2. 신용카드 또는 직불카드 등록
3. 초기 크레딧: $5 (무료 체험)

#### Step 3: API 키 생성
1. 좌측 메뉴에서 **"API keys"** 클릭
2. "Create new secret key" 버튼
3. 키 이름 입력 (예: `biz-retriever-production`)
4. **중요**: 생성된 키는 한 번만 표시됩니다! 즉시 복사
5. `.env` 파일에 입력:
   ```bash
   OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

#### 모델 선택 및 비용
| 모델 | 용도 | 비용 (1M 토큰) |
|------|------|----------------|
| `gpt-4o-mini` | 일반 분석 (권장) | $0.15 (입력) / $0.60 (출력) |
| `gpt-4o` | 정밀 분석 | $2.50 (입력) / $10.00 (출력) |
| `gpt-3.5-turbo` | 저비용 옵션 | $0.50 (입력) / $1.50 (출력) |

**권장**: `gpt-4o-mini` (성능과 비용의 균형)

#### 비용 관리
```python
# app/core/config.py에서 설정 가능
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_MAX_TOKENS = 500  # 토큰 제한으로 비용 통제
```

#### 테스트
```bash
# OpenAI API 테스트
python scripts/test_openai_api.py
```

### 발급 소요 시간
- 즉시 (결제 정보 등록 필요)

### 예상 월 비용
- 공고 100개/일 분석 시: 약 $10~30/월
- 사용량 알림 설정 권장 (Billing → Usage limits)

---

## 🔐 4. 보안 강화 설정

### SECRET_KEY 생성

#### 방법 1: OpenSSL 사용 (권장)
```bash
# Windows (Git Bash)
openssl rand -hex 32

# 출력 예시
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

#### 방법 2: Python 스크립트
```python
# scripts/generate_secret_key.py
import secrets
print(secrets.token_hex(32))
```

#### 적용
```bash
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### PostgreSQL 비밀번호

#### 강력한 비밀번호 생성
```bash
# 최소 16자, 대소문자/숫자/특수문자 포함
openssl rand -base64 24
```

#### 적용
```bash
POSTGRES_PASSWORD=Xk9mP2vL8nQ5rT3wY7zB4cF6h
```

### Redis 비밀번호

#### 생성 및 적용
```bash
# Redis 비밀번호 생성
openssl rand -base64 16

# .env에 추가
REDIS_PASSWORD=aB3dE5fG7hI9jK1l
```

#### docker-compose.yml 수정
```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
```

---

## 🌐 5. CORS 및 도메인 설정

### 프로덕션 도메인 설정

#### .env 파일
```bash
# 실제 배포 도메인
PRODUCTION_DOMAIN=https://biz-retriever.example.com

# CORS 허용 도메인 (JSON 배열 형식)
CORS_ORIGINS=["https://biz-retriever.example.com","https://www.biz-retriever.example.com"]
```

### SSL/TLS 인증서

#### 무료 인증서: Let's Encrypt
```bash
# Certbot 설치 (Ubuntu/Debian)
sudo apt-get install certbot python3-certbot-nginx

# 인증서 발급
sudo certbot --nginx -d biz-retriever.example.com
```

#### Nginx 설정 예시
```nginx
server {
    listen 443 ssl http2;
    server_name biz-retriever.example.com;

    ssl_certificate /etc/letsencrypt/live/biz-retriever.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/biz-retriever.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📦 6. 최종 .env 파일 구성

### 프로덕션 .env 템플릿

```bash
# ===========================================
# 🚀 Biz-Retriever 프로덕션 환경 설정
# ===========================================

# 기본 설정
PROJECT_NAME="Biz-Retriever Backend"
API_V1_STR="/api/v1"

# 🔐 보안 (필수 변경!)
SECRET_KEY="<openssl rand -hex 32 출력값>"
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# 🗄️ 데이터베이스
POSTGRES_SERVER=db  # Docker 사용 시
POSTGRES_USER=postgres
POSTGRES_PASSWORD="<강력한 비밀번호>"
POSTGRES_DB=bizmatch
POSTGRES_PORT=5432

# 📦 Redis
REDIS_HOST=redis  # Docker 사용 시
REDIS_PORT=6379
REDIS_PASSWORD="<강력한 비밀번호>"

# 🌐 CORS
CORS_ORIGINS=["https://your-domain.com"]
PRODUCTION_DOMAIN=https://your-domain.com

# 🤖 OpenAI
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# 📋 G2B API
G2B_API_KEY=<실제 G2B API 키>
G2B_API_ENDPOINT=https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServc01

# 📢 Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#입찰-알림

# ⚙️ 고급 설정
CRAWL_INTERVAL_HOURS=8
IMPORTANCE_THRESHOLD=2
```

---

## 🚀 7. 배포 플랫폼별 가이드

### Railway

#### 1. 프로젝트 생성
```bash
# Railway CLI 설치
npm i -g @railway/cli

# 로그인
railway login

# 프로젝트 초기화
railway init
```

#### 2. 환경 변수 설정
```bash
# 환경 변수 일괄 설정
railway variables set SECRET_KEY="your-secret-key"
railway variables set POSTGRES_PASSWORD="your-db-password"
# ... 모든 환경 변수 설정
```

#### 3. 배포
```bash
railway up
```

### AWS EC2

#### 1. 서버 설정
```bash
# Docker 설치
sudo apt-get update
sudo apt-get install docker.io docker-compose

# 프로젝트 클론
git clone https://github.com/yourusername/biz-retriever.git
cd biz-retriever
```

#### 2. 환경 변수 설정
```bash
# .env 파일 생성
nano .env
# (위의 프로덕션 .env 내용 입력)
```

#### 3. 실행
```bash
# Docker Compose로 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### Google Cloud Run

#### 1. 프로젝트 설정
```bash
# gcloud CLI 설치 및 인증
gcloud auth login
gcloud config set project your-project-id
```

#### 2. Secret Manager에 환경 변수 등록
```bash
# 각 환경 변수를 Secret으로 등록
echo -n "your-secret-key" | gcloud secrets create SECRET_KEY --data-file=-
```

#### 3. 배포
```bash
# Cloud Run 배포
gcloud run deploy biz-retriever \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

---

## ✅ 배포 후 검증

### 1. 헬스 체크
```bash
curl https://your-domain.com/health
# 예상 응답: {"status": "healthy"}
```

### 2. API 테스트
```bash
# 회원가입
curl -X POST https://your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'

# 로그인
curl -X POST https://your-domain.com/api/v1/auth/login/access-token \
  -F "username=test@example.com" \
  -F "password=SecurePass123!"
```

### 3. 크롤러 동작 확인
```bash
# 수동 크롤링 트리거 (관리자 권한 필요)
curl -X POST https://your-domain.com/api/v1/crawler/trigger \
  -H "Authorization: Bearer <your-token>"
```

### 4. Slack 알림 확인
- Slack 채널에서 공고 알림 수신 확인

---

## 📊 모니터링 및 유지보수

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f app

# 특정 서비스 로그만
docker-compose logs -f celery-worker
```

### 데이터베이스 백업
```bash
# PostgreSQL 백업
docker-compose exec db pg_dump -U postgres bizmatch > backup_$(date +%Y%m%d).sql

# 복원
docker-compose exec -T db psql -U postgres bizmatch < backup_20260123.sql
```

### 성능 모니터링
```bash
# Redis 메모리 사용량
docker-compose exec redis redis-cli INFO memory

# PostgreSQL 연결 수
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 🆘 트러블슈팅

### 문제: API 키 오류
```
해결: .env 파일에서 따옴표 제거 확인
잘못: G2B_API_KEY="key"
올바름: G2B_API_KEY=key
```

### 문제: CORS 에러
```
해결: CORS_ORIGINS 형식 확인
형식: CORS_ORIGINS=["https://domain1.com","https://domain2.com"]
```

### 문제: DB 연결 실패
```bash
# Docker 네트워크 확인
docker-compose exec app ping db

# 환경 변수 확인
docker-compose exec app env | grep POSTGRES
```

---

## 📞 지원

- **문서**: [README.md](../README.md)
- **이슈**: GitHub Issues
- **이메일**: support@your-domain.com

---

**마지막 업데이트**: 2026-01-23
**작성자**: Biz-Retriever Team
