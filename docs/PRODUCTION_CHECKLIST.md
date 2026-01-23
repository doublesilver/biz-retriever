# 🚀 프로덕션 배포 체크리스트

## 단계별 진행 상황

### Phase 1: API 키 발급 📋

#### 1-1. G2B API 키
- [ ] [공공데이터포털](https://www.data.go.kr/) 회원가입
- [ ] "조달청_입찰공고 목록조회 서비스" 활용 신청
- [ ] API 키 발급 확인
- [ ] `.env`에 `G2B_API_KEY` 입력
- [ ] 테스트: `python scripts/test_g2b_api.py`

**예상 소요 시간**: 즉시 ~ 2영업일

---

#### 1-2. Slack Webhook URL
- [ ] Slack Workspace 생성 또는 기존 사용
- [ ] 알림 채널 생성 (예: `#입찰-알림`)
- [ ] Incoming Webhooks 앱 설치
- [ ] Webhook URL 발급
- [ ] `.env`에 `SLACK_WEBHOOK_URL` 입력
- [ ] 테스트: `python scripts/test_slack_notification.py`

**예상 소요 시간**: 즉시

---

#### 1-3. OpenAI API 키
- [ ] [OpenAI Platform](https://platform.openai.com/) 계정 생성
- [ ] 결제 정보 등록 (무료 크레딧 $5)
- [ ] API 키 생성 (`biz-retriever-production`)
- [ ] `.env`에 `OPENAI_API_KEY` 입력
- [ ] 테스트: `python scripts/test_openai_api.py`
- [ ] 사용량 한도 설정 (권장: $50/월)

**예상 소요 시간**: 즉시 (결제 정보 필요)  
**예상 월 비용**: $10~30 (공고 100개/일 기준)

---

### Phase 2: 보안 설정 🔐

#### 2-1. SECRET_KEY 생성
- [ ] `python scripts/generate_secret_key.py` 실행
- [ ] 생성된 키 중 하나 선택 (Hex 방식 권장)
- [ ] `.env`에 `SECRET_KEY` 입력
- [ ] 키를 안전한 곳에 백업 (비밀번호 관리자 추천)

---

#### 2-2. 데이터베이스 비밀번호
- [ ] 강력한 비밀번호 생성 (최소 16자)
- [ ] `.env`에 `POSTGRES_PASSWORD` 입력
- [ ] `docker-compose.yml`과 일치하는지 확인

**생성 명령어**:
```bash
openssl rand -base64 24
```

---

#### 2-3. Redis 비밀번호
- [ ] Redis 비밀번호 생성
- [ ] `.env`에 `REDIS_PASSWORD` 입력
- [ ] `docker-compose.yml` 수정:
  ```yaml
  redis:
    command: redis-server --requirepass ${REDIS_PASSWORD}
  ```

**생성 명령어**:
```bash
openssl rand -base64 16
```

---

### Phase 3: 도메인 및 CORS 설정 🌐

#### 3-1. 도메인 준비
- [ ] 도메인 구매 또는 준비
- [ ] DNS 설정 (A 레코드)
- [ ] `.env`에 `PRODUCTION_DOMAIN` 입력
- [ ] `.env`에 `CORS_ORIGINS` 입력

---

#### 3-2. SSL/TLS 인증서
- [ ] Let's Encrypt Certbot 설치
- [ ] 인증서 발급
- [ ] Nginx/Caddy 설정
- [ ] HTTPS 리다이렉트 설정

---

### Phase 4: 배포 환경 선택 ☁️

다음 중 하나를 선택하세요:

#### 옵션 A: Railway (추천 - 가장 간단)
- [ ] [Railway](https://railway.app/) 계정 생성
- [ ] Railway CLI 설치
- [ ] 프로젝트 생성
- [ ] 환경 변수 설정
- [ ] 배포: `railway up`

**장점**: 무료 플랜, 자동 HTTPS, 간편한 배포  
**단점**: 무료 플랜 제한 (월 $5)

---

#### 옵션 B: AWS EC2 (프로덕션 권장)
- [ ] EC2 인스턴스 생성 (t3.small 이상)
- [ ] Docker & Docker Compose 설치
- [ ] 프로젝트 클론
- [ ] `.env` 파일 설정
- [ ] 실행: `docker-compose up -d`

**장점**: 완전한 제어, 확장성  
**단점**: 설정 복잡, 유료

---

#### 옵션 C: Google Cloud Run
- [ ] GCP 프로젝트 생성
- [ ] gcloud CLI 설치
- [ ] Secret Manager에 환경 변수 등록
- [ ] 배포: `gcloud run deploy`

**장점**: 서버리스, 자동 스케일링  
**단점**: Celery Worker 별도 관리 필요

---

### Phase 5: 배포 후 검증 ✅

#### 5-1. 헬스 체크
- [ ] `curl https://your-domain.com/health`
- [ ] 응답: `{"status": "healthy"}`

---

#### 5-2. API 테스트
- [ ] 회원가입 테스트
- [ ] 로그인 테스트
- [ ] 공고 조회 테스트
- [ ] Swagger UI 접속: `https://your-domain.com/docs`

---

#### 5-3. 크롤러 동작 확인
- [ ] 수동 크롤링 트리거
- [ ] Slack 채널에서 알림 확인
- [ ] DB에 공고 데이터 저장 확인

---

#### 5-4. 모니터링 설정
- [ ] 로그 수집 설정
- [ ] 에러 알림 설정
- [ ] 성능 모니터링 (옵션)
- [ ] 백업 스케줄 설정

---

### Phase 6: 최종 점검 🎯

#### 6-1. 보안 점검
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] SECRET_KEY가 노출되지 않았는지 확인
- [ ] API 키들이 Git에 커밋되지 않았는지 확인
- [ ] CORS 설정이 올바른지 확인

---

#### 6-2. 성능 점검
- [ ] 응답 시간 확인 (< 500ms)
- [ ] 데이터베이스 연결 풀 설정
- [ ] Redis 캐시 동작 확인
- [ ] Celery Worker 정상 동작 확인

---

#### 6-3. 문서화
- [ ] `.env.example` 업데이트
- [ ] README.md 프로덕션 섹션 추가
- [ ] API 문서 최신화
- [ ] 트러블슈팅 가이드 작성

---

## 📞 문제 발생 시

### 일반적인 문제

#### API 키 오류
```bash
# 테스트 스크립트 실행
python scripts/test_g2b_api.py
python scripts/test_slack_notification.py
python scripts/test_openai_api.py
```

#### DB 연결 실패
```bash
# Docker 네트워크 확인
docker-compose exec app ping db

# 환경 변수 확인
docker-compose exec app env | grep POSTGRES
```

#### CORS 에러
- `.env`의 `CORS_ORIGINS` 형식 확인
- 형식: `CORS_ORIGINS=["https://domain.com"]`

---

## 🎉 완료!

모든 체크리스트를 완료하면 Biz-Retriever가 프로덕션 환경에서 안정적으로 실행됩니다!

**다음 단계**: 
1. 실제 사용자 테스트
2. 피드백 수집
3. 지속적인 개선

---

**참고 문서**:
- [프로덕션 배포 가이드](./PRODUCTION_DEPLOYMENT_GUIDE.md)
- [README.md](../README.md)
- [Alembic 가이드](./ALEMBIC_GUIDE.md)
- [Redis 캐시 전략](./REDIS_CACHE_STRATEGY.md)
