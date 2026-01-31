# 라즈베리파이 수동 배포 가이드

> Tailscale SSH 연결이 안 될 때 직접 터미널에서 실행하는 가이드

## 📋 배포 전 체크리스트

- [ ] 라즈베리파이 전원 켜짐
- [ ] 모니터/키보드 연결 또는 로컬 네트워크 SSH 접속
- [ ] 인터넷 연결 확인

---

## 🚀 배포 단계 (라즈베리파이 터미널에서 실행)

### 1️⃣ 프로젝트 디렉토리 이동

```bash
cd /home/admin/projects/biz-retriever
```

### 2️⃣ 현재 상태 확인

```bash
# Git 상태
git status
git log --oneline -1

# Docker 상태
docker compose ps
```

### 3️⃣ 최신 코드 가져오기

```bash
# Git pull
git pull origin master

# 최신 커밋 확인
git log --oneline -5
```

**예상 최신 커밋:**
```
d5addc2 docs(deploy): Add Oracle Cloud Always Free Tier deployment guide
a42ea3c docs(deploy): Add Oracle Cloud Always Free Tier deployment guide
7760e03 feat(cache): Add Pydantic model serialization support
568719d docs(deploy): Add deployment instructions and automation scripts
d32dfd2 feat(security): major authentication security enhancements
```

### 4️⃣ 환경 변수 확인

```bash
# .env 파일 존재 확인
ls -la .env

# 필수 변수 확인 (비밀번호는 출력하지 않음)
grep -E '^(POSTGRES_PASSWORD|SECRET_KEY|G2B_API_KEY|GEMINI_API_KEY)=' .env | wc -l
# 출력: 4 (4개 변수가 설정되어 있어야 함)
```

### 5️⃣ 기존 컨테이너 중지

```bash
# 현재 실행 중인 컨테이너 확인
docker compose ps

# 모든 컨테이너 중지
docker compose down

# 확인
docker compose ps
# 출력: (비어있어야 함)
```

### 6️⃣ Docker 이미지 빌드 및 컨테이너 시작

**⚠️ 주의: ARM 빌드는 30-60분 소요됩니다.**

```bash
# 빌드 및 시작 (한 번에 실행)
docker compose up -d --build

# 또는 빌드만 먼저 (로그 확인 가능)
docker compose build

# 빌드 후 시작
docker compose up -d
```

**빌드 진행 중 실시간 로그 확인 (선택사항):**
```bash
# 새 터미널 열어서
docker compose logs -f
```

**빌드 중 CPU 온도 모니터링:**
```bash
# 5분마다 온도 확인
watch -n 300 vcgencmd measure_temp
```

### 7️⃣ 컨테이너 상태 확인

```bash
# 30초 대기
sleep 30

# 모든 컨테이너 상태 확인
docker compose ps
```

**예상 출력:**
```
NAME                        STATUS
biz-retriever-api           Up (healthy)
biz-retriever-db            Up (healthy)
biz-retriever-redis         Up (healthy)
biz-retriever-taskiq-worker     Up (healthy)
biz-retriever-taskiq-scheduler  Up (healthy)
```

**만약 "unhealthy" 또는 "Restarting"이 있다면:**
```bash
# 로그 확인
docker compose logs api
docker compose logs taskiq-worker

# 재시작
docker compose restart api
```

### 8️⃣ 데이터베이스 마이그레이션

```bash
# 현재 마이그레이션 버전 확인
docker compose exec api alembic current

# 마이그레이션 실행
docker compose exec api alembic upgrade head

# 마이그레이션 성공 확인
docker compose exec api alembic current
```

**예상 출력:**
```
aaab08a12b55 (head)
```

### 9️⃣ Health Check

```bash
# 로컬 Health Check
curl http://localhost:8000/health

# 예상 응답:
# {"status":"healthy","timestamp":"2026-01-31T..."}
```

**성공하면:**
```bash
# Swagger UI 접속 테스트 (브라우저)
# http://라즈베리파이_로컬IP:8000/docs
```

### 🔟 Tailscale Funnel 확인 (외부 접속용)

```bash
# Tailscale 상태 확인
sudo tailscale status

# Tailscale Funnel 상태 확인
sudo tailscale serve status

# 외부 URL로 Health Check (다른 PC에서)
curl https://leeeunseok.tail32c3e2.ts.net/health
```

**Tailscale Funnel이 안 되면:**
```bash
# Tailscale 재시작
sudo systemctl restart tailscaled
sudo tailscale up

# Funnel 재설정 (필요시)
sudo tailscale funnel 8000
```

---

## ✅ 배포 완료 확인

모든 단계가 성공하면:

1. **로컬 접속 확인**
   ```
   http://localhost:8000/docs
   ```

2. **로컬 네트워크 접속 확인**
   ```bash
   # 라즈베리파이 로컬 IP 확인
   hostname -I
   
   # 출력: 192.168.x.x (첫 번째 IP 사용)
   # 브라우저에서: http://192.168.x.x:8000/docs
   ```

3. **외부 접속 확인**
   ```
   https://leeeunseok.tail32c3e2.ts.net/docs
   ```

---

## 🧪 기능 테스트

### 1. 회원가입 테스트

Swagger UI (`/docs`)에서:
1. `POST /api/v1/auth/register` 엔드포인트 찾기
2. Try it out 클릭
3. 테스트 데이터 입력:
   ```json
   {
     "email": "test@example.com",
     "password": "TestPass123!"
   }
   ```
4. Execute 클릭
5. 응답 확인: `201 Created`

### 2. 로그인 테스트

1. `POST /api/v1/auth/login/access-token` 엔드포인트
2. Form data 입력:
   - username: `test@example.com`
   - password: `TestPass123!`
3. 응답에서 `access_token` 확인

### 3. 로그아웃 테스트 (NEW!)

1. 로그인해서 받은 `access_token` 복사
2. 페이지 상단 "Authorize" 버튼 클릭
3. `Bearer <access_token>` 입력
4. `POST /api/v1/auth/logout` 엔드포인트 실행
5. 응답 확인: `{"message": "Successfully logged out"}`

### 4. 계정 잠금 테스트 (NEW!)

1. 의도적으로 틀린 비밀번호로 5회 로그인 시도
2. 6번째 시도 시 에러 확인:
   ```json
   {
     "detail": "Account locked due to too many failed login attempts. Try again in 30 minutes."
   }
   ```

---

## 🔧 트러블슈팅

### 빌드 실패

```bash
# 디스크 공간 확인
df -h
# 10GB 이상 필요

# 메모리 확인
free -h
# swap이 켜져있는지 확인

# Docker 캐시 정리
docker system prune -a
docker volume prune

# 재시도
docker compose build
```

### 컨테이너가 계속 재시작됨

```bash
# API 로그 확인
docker compose logs --tail=100 api

# 데이터베이스 연결 확인
docker compose exec api ping postgres

# 환경 변수 확인
docker compose exec api env | grep -E 'POSTGRES|REDIS|SECRET'
```

### Health Check 실패

```bash
# API가 실행 중인지 확인
docker compose ps api

# API 로그 확인
docker compose logs api

# 포트 확인
sudo netstat -tlnp | grep 8000
```

### Tailscale 연결 안 됨

```bash
# Tailscale 상태
sudo tailscale status

# Tailscale 재시작
sudo systemctl restart tailscaled
sudo tailscale up

# 로그 확인
sudo journalctl -u tailscaled -n 50
```

---

## 📊 모니터링

### 실시간 로그 확인

```bash
# 모든 서비스
docker compose logs -f

# 특정 서비스만
docker compose logs -f api
docker compose logs -f taskiq-worker

# 에러만 필터링
docker compose logs | grep -i error
```

### 리소스 사용량

```bash
# Docker 컨테이너 리소스
docker stats

# 시스템 전체
htop

# 디스크 사용량
df -h

# 메모리 사용량
free -h

# CPU 온도
vcgencmd measure_temp
```

---

## 🎯 주요 변경사항 (2026-01-31)

이번 배포에 포함된 보안 강화:

1. **OAuth2 제거**
   - Kakao, Naver 소셜 로그인 제거
   - 이메일/비밀번호 인증만 사용

2. **계정 잠금**
   - 로그인 5회 실패 시 30분 자동 잠금
   - `failed_login_attempts`, `locked_until` 필드 추가

3. **로그아웃 엔드포인트**
   - `POST /api/v1/auth/logout`
   - Redis 기반 토큰 블랙리스트

4. **토큰 보안 강화**
   - Access Token: 8일 → **15분**
   - Refresh Token: 30일 (신규)
   - Token Rotation

5. **Pydantic 캐시 개선**
   - `model_dump()` 직렬화 지원

---

## 📞 도움이 필요하면

1. 로그 확인:
   ```bash
   docker compose logs --tail=200 > deployment_error.log
   ```

2. 시스템 정보 수집:
   ```bash
   # 시스템 정보
   uname -a > system_info.txt
   free -h >> system_info.txt
   df -h >> system_info.txt
   vcgencmd measure_temp >> system_info.txt
   
   # Docker 정보
   docker compose ps >> system_info.txt
   docker compose config >> system_info.txt
   ```

3. 파일 공유 후 문의

---

**배포 성공을 기원합니다! 🚀**

**Last Updated**: 2026-01-31  
**Estimated Time**: 30-90분 (빌드 시간 포함)
