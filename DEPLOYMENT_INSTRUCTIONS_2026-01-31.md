# 🚀 Biz-Retriever 라즈베리파이 배포 가이드 (2026-01-31)

## 배포 개요

**배포 일시**: 2026년 1월 31일  
**배포 내용**: 보안 강화 업데이트 (OAuth 제거, 계정 잠금, 로그아웃 기능)  
**예상 시간**: 약 15-20분  
**다운타임**: 약 3-5분 (Docker 재시작)

---

## 📋 사전 확인 사항

### 1. 라즈베리파이 접속 정보
- **IP 주소**: 100.75.72.6 (Tailscale 내부 IP)
- **사용자**: admin
- **프로젝트 경로**: `/home/admin/projects/biz-retriever`
- **접속 방법**: `ssh admin@100.75.72.6`

### 2. 현재 서비스 상태 확인
```bash
# Tailscale 연결 확인
tailscale status

# 현재 서비스 URL 테스트
curl -I https://leeeunseok.tail32c3e2.ts.net/health
```

---

## 🔧 배포 절차

### Step 1: 라즈베리파이 접속
```bash
# Windows PowerShell 또는 Git Bash에서 실행
ssh admin@100.75.72.6
```

### Step 2: 프로젝트 디렉토리 이동
```bash
cd /home/admin/projects/biz-retriever
```

### Step 3: 현재 서비스 상태 백업
```bash
# 현재 실행 중인 서비스 확인
docker-compose ps

# 현재 Git 상태 확인
git status
git log --oneline -1
```

### Step 4: 최신 코드 가져오기
```bash
# 원격 저장소에서 최신 코드 가져오기
git pull origin master

# 변경사항 확인
git log --oneline -5
```

**예상 출력:**
```
344e406 Merge branch 'master' of https://github.com/doublesilver/biz-retriever
d32dfd2 feat(security): major authentication security enhancements
17a12a5 fix(test): Add test and testserver to TrustedHost allowed_hosts
...
```

### Step 5: ⚠️ CRITICAL - 데이터베이스 마이그레이션 실행
```bash
# Docker 컨테이너 내부에서 마이그레이션 실행
docker-compose exec api alembic upgrade head
```

**예상 출력:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 80f06c107978 -> aaab08a12b55, add_user_security_fields
```

**⚠️ 만약 마이그레이션 에러 발생 시:**
```bash
# 현재 마이그레이션 상태 확인
docker-compose exec api alembic current

# 마이그레이션 히스토리 확인
docker-compose exec api alembic history

# 특정 버전으로 강제 설정 (최후의 수단)
docker-compose exec api alembic stamp aaab08a12b55
```

### Step 6: Docker 서비스 재시작
```bash
# 기존 서비스 중지
docker-compose down

# 새 이미지 빌드 (필요시)
docker-compose build --no-cache api

# 서비스 시작
docker-compose -f docker-compose.pi.yml up -d

# 서비스 상태 확인
docker-compose ps
```

**모든 서비스가 "Up" 상태여야 함:**
```
NAME                       STATUS
biz-retriever-api          Up (healthy)
biz-retriever-db           Up (healthy)
biz-retriever-redis        Up (healthy)
biz-retriever-worker       Up
biz-retriever-scheduler    Up
biz-retriever-frontend     Up (healthy)
biz-retriever-prometheus   Up (healthy)
biz-retriever-grafana      Up (healthy)
```

### Step 7: 서비스 로그 확인
```bash
# API 서비스 로그 확인 (최근 50줄)
docker-compose logs --tail=50 api

# Worker 로그 확인
docker-compose logs --tail=50 taskiq-worker

# 에러 로그만 확인
docker-compose logs | grep -i error
```

### Step 8: Health Check 테스트
```bash
# 로컬 health check
curl http://localhost:8000/health

# 외부 URL health check (Tailscale Funnel)
curl https://leeeunseok.tail32c3e2.ts.net/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected"
}
```

### Step 9: API 기능 테스트
```bash
# Swagger UI 접속 테스트
curl -I https://leeeunseok.tail32c3e2.ts.net/docs

# 로그인 테스트 (옵션)
curl -X POST "https://leeeunseok.tail32c3e2.ts.net/api/v1/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=yourpassword"
```

### Step 10: 모니터링 확인
```bash
# Prometheus 접속 (로컬)
curl http://localhost:9090/-/healthy

# Grafana 접속 (로컬)
curl http://localhost:3000/api/health
```

---

## 🔍 배포 검증 체크리스트

### ✅ 필수 확인 사항
- [ ] Git pull 성공 (최신 커밋: d32dfd2)
- [ ] 데이터베이스 마이그레이션 성공 (aaab08a12b55)
- [ ] Docker 서비스 모두 "Up (healthy)" 상태
- [ ] API health check 성공 (http://localhost:8000/health)
- [ ] Tailscale Funnel URL 접속 가능 (https://leeeunseok.tail32c3e2.ts.net/)
- [ ] Swagger UI 접속 가능 (/docs)
- [ ] 로그에 에러 없음

### ✅ 기능 확인 사항
- [ ] 회원가입 테스트
- [ ] 로그인 테스트 (실패 5회 → 30분 잠금 확인)
- [ ] 로그아웃 테스트 (토큰 블랙리스트 확인)
- [ ] 토큰 갱신 테스트 (/auth/refresh)

---

## 🚨 트러블슈팅

### 문제 1: 마이그레이션 에러
**증상**: `alembic upgrade head` 실패
**해결**:
```bash
# 현재 상태 확인
docker-compose exec api alembic current

# 마이그레이션 재시도
docker-compose exec api alembic upgrade head --sql

# 수동 마이그레이션 (최후의 수단)
docker-compose exec api python -c "
from app.db.session import engine
import sqlalchemy as sa
with engine.begin() as conn:
    conn.execute(sa.text('ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0'))
    conn.execute(sa.text('ALTER TABLE users ADD COLUMN locked_until TIMESTAMP'))
    conn.execute(sa.text('ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP'))
"
```

### 문제 2: Docker 컨테이너가 시작하지 않음
**증상**: `docker-compose ps`에서 "Restarting" 또는 "Exited" 상태
**해결**:
```bash
# 로그 확인
docker-compose logs api

# 이미지 재빌드
docker-compose build --no-cache api

# 컨테이너 강제 재생성
docker-compose up -d --force-recreate api
```

### 문제 3: 외부 URL 접속 불가
**증상**: https://leeeunseok.tail32c3e2.ts.net/ 접속 실패
**해결**:
```bash
# Tailscale Funnel 상태 확인
tailscale serve status

# Funnel 재시작
tailscale serve reset
tailscale serve / http://localhost:3001
```

### 문제 4: Redis 연결 실패
**증상**: `redis.exceptions.ConnectionError`
**해결**:
```bash
# Redis 컨테이너 재시작
docker-compose restart redis

# Redis 로그 확인
docker-compose logs redis

# Redis 연결 테스트
docker-compose exec redis redis-cli ping
```

---

## 📊 배포 후 모니터링

### 1. Grafana 대시보드 확인
```
URL: http://100.75.72.6:3000
계정: admin / (GRAFANA_ADMIN_PASSWORD)
```

**확인 사항:**
- CPU 사용률 (< 80%)
- 메모리 사용률 (< 3.5GB / 4GB)
- API 응답 시간 (< 500ms)
- 에러율 (< 1%)

### 2. Prometheus Alerts 확인
```
URL: http://100.75.72.6:9090/alerts
```

**확인 사항:**
- 활성 알림 개수 (0개가 정상)
- Alert 규칙 상태 (모두 "OK")

### 3. 로그 모니터링
```bash
# 실시간 로그 확인
docker-compose logs -f api

# 에러 로그만 필터링
docker-compose logs -f | grep -i "error\|exception\|failed"
```

---

## 📝 배포 완료 보고 템플릿

```
배포 완료 보고 (2026-01-31)

✅ 배포 성공
- Git 커밋: d32dfd2
- 마이그레이션: aaab08a12b55 ✅
- Docker 서비스: 11/11 Running ✅
- Health Check: PASS ✅
- Swagger UI: PASS ✅
- Monitoring: PASS ✅

🔗 서비스 URL
- API: https://leeeunseok.tail32c3e2.ts.net/
- Swagger: https://leeeunseok.tail32c3e2.ts.net/docs
- Grafana: http://100.75.72.6:3000

🔒 주요 변경사항
- OAuth2 제거 (Kakao, Naver)
- 계정 잠금 기능 추가 (5회 실패 → 30분)
- 로그아웃 엔드포인트 추가
- Access Token 유효기간 단축 (8일 → 15분)

⏱️ 배포 시간
- 시작: [시간]
- 종료: [시간]
- 소요 시간: [분]
- 다운타임: [분]

📋 다음 단계
- [ ] 고객사에게 변경사항 안내
- [ ] 사용자 매뉴얼 업데이트
- [ ] 1주일간 모니터링 강화
```

---

## 🔐 보안 참고사항

**중요한 변경사항:**
1. **OAuth2 제거**: Kakao/Naver 소셜 로그인 더 이상 사용 불가
2. **계정 잠금**: 로그인 5회 실패 시 30분 자동 잠금
3. **로그아웃**: `/api/v1/auth/logout` 엔드포인트 추가
4. **토큰 유효기간**: Access Token 15분, Refresh Token 30일

**고객사에게 안내할 사항:**
- 소셜 로그인 사용자는 이메일/비밀번호로 재등록 필요
- 로그인 실패 시 5회 제한 있음
- 로그아웃 기능 사용 가능

---

## 📞 문제 발생 시 연락처

**긴급 연락처**: [담당자]  
**Slack 채널**: #biz-retriever-alerts  
**GitHub Issues**: https://github.com/doublesilver/biz-retriever/issues

---

**배포 담당**: doublesilver  
**작성일**: 2026-01-31  
**문서 버전**: 1.0
