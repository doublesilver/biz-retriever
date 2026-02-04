# 🕐 Cron 자동화 설정 가이드

**작성일**: 2026-02-04  
**플랫폼**: Vercel Serverless (Hobby Plan)  
**권장 방법**: 외부 Cron 서비스 (무료)

---

## 📌 왜 외부 Cron 서비스가 필요한가?

### Vercel Hobby Plan 제한
- ✅ **무료**: $0/월
- ❌ **Cron 제한**: 1일 1회만 스케줄 가능
- ❌ **현재 필요**: 하루 4개 Cron Job (총 6회 실행)

| Cron Job | 스케줄 | 필요 횟수 |
|----------|--------|-----------|
| `crawl-g2b.py` | 08:00, 12:00, 18:00 | 3회/일 |
| `morning-digest.py` | 08:30 | 1회/일 |
| `renew-subscriptions.py` | 00:00 | 1회/일 |
| **합계** | | **5회/일** |

### 해결 방안

| 옵션 | 비용 | 제한 | 권장 |
|------|------|------|------|
| **Option A: Vercel Pro** | $20/월 | 무제한 Cron | ❌ 비용 발생 |
| **Option B: 외부 서비스** | 무료 | 플랫폼마다 상이 | ✅ **권장** |

---

## 🚀 추천 무료 Cron 서비스

### 1. **cron-job.org** (권장)
- ✅ **무료**: 영구 무료
- ✅ **제한**: 50개 Cron Jobs
- ✅ **최소 간격**: 1분
- ✅ **모니터링**: 실행 로그 제공
- ✅ **알림**: 실패 시 이메일 알림
- ✅ **URL**: https://cron-job.org

### 2. **EasyCron**
- ✅ **무료 플랜**: 월 1,000회 실행
- ✅ **제한**: 1일 33회 (충분)
- ❌ **최소 간격**: 5분 (제한적)

### 3. **cron-job.io**
- ✅ **무료**: 영구 무료
- ✅ **제한**: 10개 Cron Jobs
- ✅ **최소 간격**: 1분

---

## 📋 설정 방법: cron-job.org

### Step 1: 계정 생성
1. https://cron-job.org 접속
2. "Sign Up" 클릭
3. 이메일 인증 완료

### Step 2: CRON_SECRET 확인
Vercel 환경변수에 설정된 `CRON_SECRET` 확인:

```bash
vercel env ls production --token YOUR_VERCEL_TOKEN
```

**중요**: Cron 엔드포인트는 `Authorization: Bearer CRON_SECRET` 헤더가 필요합니다.

### Step 3: Cron Job 생성

#### ① G2B 크롤링 (하루 3회)

**Cron #1: 오전 8시**
- **Title**: `Biz-Retriever: G2B Crawl (08:00)`
- **URL**: `https://sideproject-one.vercel.app/api/cron/crawl-g2b`
- **Schedule**: `0 8 * * *` (매일 08:00 KST)
- **HTTP Method**: `GET`
- **Headers**:
  ```
  Authorization: Bearer YOUR_CRON_SECRET
  ```
- **Expected Response**: `200 OK`

**Cron #2: 낮 12시**
- **Title**: `Biz-Retriever: G2B Crawl (12:00)`
- **URL**: `https://sideproject-one.vercel.app/api/cron/crawl-g2b`
- **Schedule**: `0 12 * * *` (매일 12:00 KST)
- **HTTP Method**: `GET`
- **Headers**:
  ```
  Authorization: Bearer YOUR_CRON_SECRET
  ```

**Cron #3: 저녁 6시**
- **Title**: `Biz-Retriever: G2B Crawl (18:00)`
- **URL**: `https://sideproject-one.vercel.app/api/cron/crawl-g2b`
- **Schedule**: `0 18 * * *` (매일 18:00 KST)
- **HTTP Method**: `GET`
- **Headers**:
  ```
  Authorization: Bearer YOUR_CRON_SECRET
  ```

---

#### ② 모닝 브리핑 (하루 1회)

**Cron #4: 오전 8시 30분**
- **Title**: `Biz-Retriever: Morning Digest (08:30)`
- **URL**: `https://sideproject-one.vercel.app/api/cron/morning-digest`
- **Schedule**: `30 8 * * *` (매일 08:30 KST)
- **HTTP Method**: `GET`
- **Headers**:
  ```
  Authorization: Bearer YOUR_CRON_SECRET
  ```
- **Expected Response**: `200 OK`

---

#### ③ 구독 갱신 (하루 1회)

**Cron #5: 자정**
- **Title**: `Biz-Retriever: Renew Subscriptions (00:00)`
- **URL**: `https://sideproject-one.vercel.app/api/cron/renew-subscriptions`
- **Schedule**: `0 0 * * *` (매일 00:00 KST)
- **HTTP Method**: `GET`
- **Headers**:
  ```
  Authorization: Bearer YOUR_CRON_SECRET
  ```
- **Expected Response**: `200 OK`

---

### Step 4: 알림 설정 (선택)

**Failure Notification**:
1. cron-job.org 대시보드 → Settings
2. "Email Notifications" 활성화
3. 실패 시 이메일 수신

---

## 🧪 테스트 방법

### 로컬 테스트 (수동 실행)

```bash
# CRON_SECRET 확인
CRON_SECRET="your_cron_secret_here"

# 1. G2B 크롤링 테스트
curl -X GET https://sideproject-one.vercel.app/api/cron/crawl-g2b \
  -H "Authorization: Bearer $CRON_SECRET" \
  -v

# Expected: 200 OK, JSON response with crawl results

# 2. 모닝 브리핑 테스트
curl -X GET https://sideproject-one.vercel.app/api/cron/morning-digest \
  -H "Authorization: Bearer $CRON_SECRET" \
  -v

# Expected: 200 OK, Slack notification sent

# 3. 구독 갱신 테스트
curl -X GET https://sideproject-one.vercel.app/api/cron/renew-subscriptions \
  -H "Authorization: Bearer $CRON_SECRET" \
  -v

# Expected: 200 OK, subscriptions renewed
```

### 실행 로그 확인

```bash
# Vercel 로그 확인
vercel logs --token YOUR_VERCEL_TOKEN

# 특정 함수 로그만 보기
vercel logs --token YOUR_VERCEL_TOKEN | grep "crawl-g2b"
```

---

## 📊 Cron 스케줄 요약

| 시간 (KST) | Cron Job | 설명 |
|-----------|----------|------|
| **00:00** | renew-subscriptions | 구독 갱신 처리 |
| **08:00** | crawl-g2b | G2B 크롤링 (1차) |
| **08:30** | morning-digest | 모닝 브리핑 Slack 알림 |
| **12:00** | crawl-g2b | G2B 크롤링 (2차) |
| **18:00** | crawl-g2b | G2B 크롤링 (3차) |

**총 실행 횟수**: 5회/일

---

## 🔒 보안 고려사항

### ✅ 구현된 보안
- **CRON_SECRET 인증**: `Authorization: Bearer` 헤더 필수
- **Vercel 환경변수**: CRON_SECRET 암호화 저장
- **실패 알림**: 비정상 실행 즉시 감지

### ⚠️ 주의사항
- **CRON_SECRET 노출 금지**: GitHub 커밋 절대 금지
- **로그 모니터링**: Vercel 로그에서 에러 확인
- **IP 화이트리스트**: 필요 시 cron-job.org IP 제한

---

## 🛠️ 문제 해결

### 문제 1: 401 Unauthorized
**증상**: `{"error": "Unauthorized"}`

**원인**: CRON_SECRET 불일치

**해결**:
```bash
# Vercel 환경변수 확인
vercel env ls production --token YOUR_VERCEL_TOKEN

# CRON_SECRET이 올바른지 확인
# cron-job.org 헤더에 동일한 값 입력
```

---

### 문제 2: 500 Internal Server Error
**증상**: `{"error": "Internal server error"}`

**원인**: DB 연결 실패, API 에러 등

**해결**:
```bash
# Vercel 로그 확인
vercel logs --token YOUR_VERCEL_TOKEN | tail -50

# DB 연결 확인
# NEON_DATABASE_URL 환경변수 확인
```

---

### 문제 3: Cron Job이 실행되지 않음
**증상**: cron-job.org 로그에 "Connection timeout"

**원인**: Vercel Serverless Cold Start (첫 실행 지연)

**해결**:
- **Timeout 설정**: cron-job.org에서 Timeout을 30초로 증가
- **Retry 설정**: 실패 시 1번 재시도

---

## 📈 모니터링 및 최적화

### 실행 로그 분석
```bash
# 최근 24시간 Cron 실행 확인
vercel logs --token YOUR_VERCEL_TOKEN --since 24h | grep "cron"

# 에러만 필터링
vercel logs --token YOUR_VERCEL_TOKEN --since 24h | grep "ERROR"
```

### 성능 최적화
- **Cold Start 최소화**: Health Check 엔드포인트 추가 (5분마다 Ping)
- **병렬 실행**: 크롤링 작업 비동기 처리
- **캐싱**: Redis에 중복 공고 체크

---

## 🎯 다음 단계

1. ✅ **cron-job.org 계정 생성**
2. ✅ **5개 Cron Job 설정**
3. ✅ **수동 테스트 실행**
4. ✅ **24시간 모니터링**
5. ✅ **에러 알림 확인**

---

## 📝 체크리스트

```
[ ] cron-job.org 계정 생성
[ ] CRON_SECRET 확인 (Vercel 환경변수)
[ ] Cron #1: G2B Crawl 08:00 설정
[ ] Cron #2: G2B Crawl 12:00 설정
[ ] Cron #3: G2B Crawl 18:00 설정
[ ] Cron #4: Morning Digest 08:30 설정
[ ] Cron #5: Renew Subscriptions 00:00 설정
[ ] 수동 테스트 실행 (5개 엔드포인트)
[ ] Vercel 로그 확인
[ ] 실패 알림 이메일 설정
[ ] 24시간 모니터링 완료
```

---

## 🔗 참고 링크

- **cron-job.org**: https://cron-job.org
- **Vercel 대시보드**: https://vercel.com/doublesilvers-projects/sideproject
- **Vercel 로그**: `vercel logs --token YOUR_VERCEL_TOKEN`
- **Cron Expression 생성기**: https://crontab.guru

---

**작성자**: Claude (Sisyphus Agent)  
**작성일**: 2026-02-04  
**프로젝트**: Biz-Retriever  
**버전**: 1.0.0
