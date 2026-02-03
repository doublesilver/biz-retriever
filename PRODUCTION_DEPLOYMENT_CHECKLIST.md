# 🚀 프로덕션 배포 체크리스트

Vercel 서버리스 환경으로의 완전한 마이그레이션을 위한 최종 체크리스트입니다.

---

## 📋 배포 전 체크리스트

### 1. 환경 설정 완료 확인

- [ ] **Neon Postgres**
  - [ ] 데이터베이스 생성 완료
  - [ ] 스키마 마이그레이션 완료 (`alembic upgrade head`)
  - [ ] 연결 테스트 성공 (`scripts/migrate-to-neon.sh`)
  - [ ] 테이블 12개 생성 확인

- [ ] **Upstash Redis**
  - [ ] Redis 인스턴스 생성 완료
  - [ ] 연결 테스트 성공 (`scripts/test-upstash.sh`)
  - [ ] PING/SET/GET 동작 확인

- [ ] **Vercel 환경 변수**
  - [ ] `NEON_DATABASE_URL` 설정 (production, preview, development)
  - [ ] `UPSTASH_REDIS_URL` 설정 (production, preview, development)
  - [ ] `SECRET_KEY` 설정 (32+ chars)
  - [ ] `CRON_SECRET` 설정 (32+ chars)
  - [ ] `GEMINI_API_KEY` 설정 (선택)
  - [ ] `G2B_API_KEY` 설정 (선택)
  - [ ] `SLACK_WEBHOOK_URL` 설정 (선택)

### 2. 코드 검증

- [ ] **로컬 테스트 통과**
  - [ ] `pytest tests/ -v` 실행
  - [ ] 최소 85% 이상 통과 (147/169 이상)
  - [ ] Critical 테스트 모두 통과

- [ ] **Git 상태 정리**
  - [ ] 모든 변경사항 커밋됨
  - [ ] `feature/vercel-migration` 브랜치 최신화
  - [ ] Merge conflict 없음

### 3. Preview 배포 검증

- [ ] **Preview 배포 성공**
  - [ ] `./scripts/deploy-preview.sh` 실행 성공
  - [ ] Preview URL 생성됨

- [ ] **자동 검증 통과**
  - [ ] `./scripts/verify-deployment.sh` 모든 테스트 통과
  - [ ] Health check 응답
  - [ ] API docs 접근 가능
  - [ ] Frontend 로딩

- [ ] **수동 검증**
  - [ ] 로그인 페이지 접속
  - [ ] 회원가입 동작 확인
  - [ ] 로그인 동작 확인
  - [ ] Dashboard 로딩 확인
  - [ ] Kanban 보드 동작 확인
  - [ ] 프로필 편집 동작 확인

- [ ] **기능 테스트**
  - [ ] 입찰 공고 목록 조회
  - [ ] AI 분석 기능 동작 (Gemini API 설정 시)
  - [ ] Excel 내보내기 동작
  - [ ] 키워드 관리 동작
  - [ ] SSE 알림 동작 (브라우저 Console 확인)

### 4. 성능 및 보안

- [ ] **응답 시간**
  - [ ] Health check < 1초
  - [ ] API 평균 응답 시간 < 3초
  - [ ] Frontend 초기 로딩 < 5초

- [ ] **보안 헤더 확인**
  - [ ] CORS 헤더 올바르게 설정
  - [ ] X-Frame-Options: DENY
  - [ ] X-Content-Type-Options: nosniff
  - [ ] X-XSS-Protection 설정

- [ ] **에러 핸들링**
  - [ ] 프로덕션 환경에서 상세 에러 메시지 숨김
  - [ ] 로그에만 에러 상세 기록
  - [ ] 사용자에게는 친화적인 메시지 표시

---

## 🚀 프로덕션 배포 절차

### Step 1: 최종 코드 리뷰

```bash
# 모든 변경사항 확인
git diff master feature/vercel-migration

# 중요 파일 검토
git show feature/vercel-migration:api/index.py
git show feature/vercel-migration:vercel.json
git show feature/vercel-migration:app/core/config.py
```

### Step 2: Master 브랜치로 병합

```bash
# Master로 전환
git checkout master

# 최신 상태 확인
git pull origin master

# Feature 브랜치 병합
git merge feature/vercel-migration

# 충돌 해결 (있는 경우)
# ... resolve conflicts ...
# git add .
# git commit -m "Merge feature/vercel-migration"
```

### Step 3: 태그 생성 (버전 관리)

```bash
# 버전 태그 생성
git tag -a v1.0.0-vercel -m "Production deployment on Vercel serverless"

# 태그 푸시
git push origin v1.0.0-vercel
```

### Step 4: 프로덕션 배포

```bash
# Master 푸시 (자동 배포 트리거)
git push origin master

# 또는 수동 배포
vercel --prod
```

### Step 5: 배포 모니터링

```bash
# 실시간 로그 확인
vercel logs --prod --follow

# 또는 Vercel Dashboard에서 확인
# https://vercel.com/dashboard
```

---

## ✅ 배포 후 검증

### 1. 프로덕션 URL 테스트

**Production URL**: https://biz-retriever.vercel.app

```bash
# 자동 검증 스크립트 실행
./scripts/verify-deployment.sh https://biz-retriever.vercel.app

# 수동 확인
curl https://biz-retriever.vercel.app/health
open https://biz-retriever.vercel.app/docs
open https://biz-retriever.vercel.app/
```

### 2. 전체 기능 테스트

- [ ] **회원가입/로그인**
  - [ ] 새 계정 생성 가능
  - [ ] JWT 토큰 발급 확인
  - [ ] 로그인 상태 유지

- [ ] **대시보드**
  - [ ] 통계 카드 표시
  - [ ] 입찰 공고 목록 로딩
  - [ ] 필터링 동작
  - [ ] 검색 동작

- [ ] **칸반 보드**
  - [ ] 4개 컬럼 표시
  - [ ] 드래그앤드롭 동작
  - [ ] 상태 변경 저장

- [ ] **키워드 관리**
  - [ ] 키워드 추가/삭제
  - [ ] Redis 캐시 업데이트

- [ ] **프로필**
  - [ ] 정보 수정 가능
  - [ ] 사업자등록증 업로드 (Gemini 분석)
  - [ ] 구독 플랜 변경

### 3. Cron Jobs 확인

**Cron 스케줄**:
- G2B 크롤링: 매일 08:00, 12:00, 18:00 (KST)
- 모닝 다이제스트: 매일 08:30 (KST)

```bash
# 30분 후 로그 확인
vercel logs --prod | grep cron

# Cron Job이 실행되었는지 확인
# - /api/cron/crawl-g2b
# - /api/cron/morning-digest
```

### 4. 성능 모니터링

- [ ] **Vercel Analytics 확인**
  - Dashboard → Analytics
  - Request 수, 응답 시간, 에러율 확인

- [ ] **Database 모니터링**
  - Neon Console → Metrics
  - Connection pool 사용률 확인
  - Query 성능 확인

- [ ] **Redis 모니터링**
  - Upstash Console → Metrics
  - 요청 수, 히트율 확인

---

## 🔧 Troubleshooting

### 문제: 데이터베이스 연결 실패

**증상**: `psycopg2.OperationalError: could not connect to server`

**해결책**:
1. Neon Console에서 데이터베이스 상태 확인
2. Connection string에 `?pgbouncer=true` 포함 확인
3. Vercel 환경 변수 재확인: `vercel env ls | grep NEON`
4. Neon IP allowlist 확인 (Vercel IP 허용)

```bash
# 연결 테스트
psql "$(vercel env pull --prod | grep NEON_DATABASE_URL | cut -d'=' -f2)"
```

### 문제: Redis 연결 실패

**증상**: `redis.exceptions.ConnectionError`

**해결책**:
1. Upstash Console에서 Redis 상태 확인
2. Connection string 형식 확인 (`redis://default:password@host:port`)
3. Vercel 환경 변수 재확인: `vercel env ls | grep UPSTASH`

```bash
# 연결 테스트
redis-cli -u "$(vercel env pull --prod | grep UPSTASH_REDIS_URL | cut -d'=' -f2)"
```

### 문제: Cron Job이 실행되지 않음

**증상**: 예정된 시간에 크롤링이 실행되지 않음

**해결책**:
1. `vercel.json`의 cron 스케줄 확인
2. `CRON_SECRET` 환경 변수 설정 확인
3. Cron 엔드포인트 수동 호출 테스트:
   ```bash
   curl -X POST https://biz-retriever.vercel.app/api/cron/crawl-g2b \
     -H "Authorization: Bearer YOUR_CRON_SECRET"
   ```
4. Vercel Dashboard → Cron Jobs 탭에서 실행 이력 확인

### 문제: 500 Internal Server Error

**증상**: API 호출 시 500 에러

**해결책**:
1. Vercel 로그 확인: `vercel logs --prod --follow`
2. 환경 변수 누락 확인
3. 데이터베이스 스키마 마이그레이션 확인
4. 코드 에러 확인 (try-except 블록)

---

## 🔄 롤백 절차

배포 후 심각한 문제 발생 시:

### 방법 1: Vercel Dashboard에서 롤백

1. Vercel Dashboard → Deployments
2. 이전 배포 선택
3. "Promote to Production" 클릭

### 방법 2: Git Revert

```bash
# 최근 커밋 되돌리기
git checkout master
git revert HEAD
git push origin master

# Vercel이 자동으로 재배포
```

### 방법 3: 태그로 복원

```bash
# 백업 태그로 복원
git checkout backup-pre-vercel-migration
git push origin master --force

# ⚠️ 주의: --force는 신중하게 사용
```

---

## 📊 배포 완료 보고

배포가 성공적으로 완료되면 다음 정보를 기록하세요:

```
✅ 프로덕션 배포 완료

- 배포 일시: 2026-02-03 18:00 (KST)
- 배포 버전: v1.0.0-vercel
- 커밋 해시: e85423a
- Production URL: https://biz-retriever.vercel.app
- 배포 환경: Vercel Serverless (Python 3.11)
- 데이터베이스: Neon Postgres (pgbouncer enabled)
- 캐시: Upstash Redis
- 테스트 통과율: 87% (147/169)
- 응답 시간: Health check < 500ms
- Cron Jobs: 정상 동작 확인

주요 변경사항:
- Raspberry Pi → Vercel 서버리스 완전 마이그레이션
- WebSocket → SSE 전환
- Taskiq → Vercel Cron Jobs 전환
- 로컬 DB/Redis → Neon/Upstash 전환
```

---

## 🎉 마이그레이션 완료!

축하합니다! Biz-Retriever가 성공적으로 Vercel 서버리스 환경으로 마이그레이션되었습니다.

**다음 단계**:
1. ✅ 일주일간 모니터링
2. ✅ 사용자 피드백 수집
3. ✅ 성능 최적화
4. ✅ 추가 기능 개발

**유지보수 체크리스트**:
- [ ] 주간 로그 리뷰
- [ ] 월간 성능 보고서
- [ ] Neon/Upstash 사용량 모니터링
- [ ] 보안 업데이트 적용

---

**문서 버전**: 1.0  
**마지막 업데이트**: 2026-02-03  
**담당자**: Sisyphus (OhMyClaude Code)
