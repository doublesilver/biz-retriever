# 🎯 Vercel Storage 옵션 비교 가이드

## 📊 중요 발견!

Vercel은 **두 가지 Storage 방식**을 제공합니다:

1. **Vercel Storage** (자체 제공) - Vercel Postgres & Vercel KV
2. **Marketplace 통합** (외부 제공자) - Neon, Supabase, Upstash 등

---

## 🔍 옵션 상세 비교

### Option A: Vercel Storage (자체 제공) ⭐⭐⭐

**구성:**
- Vercel Postgres (Vercel 직접 제공)
- Vercel KV (Vercel 직접 제공)

**무료 티어:**
| 리소스 | 제한 |
|--------|------|
| Postgres 저장소 | 256MB |
| Postgres 실행 시간 | 60시간/월 |
| KV 메모리 | 256MB |
| KV 요청 | 10,000/일 |

**장점:**
- ✅ **설정 가장 간단** (Vercel 대시보드만 사용)
- ✅ **환경 변수 자동 주입**
- ✅ **통합 빌링** (Vercel 계정 하나로 관리)
- ✅ **계정 추가 불필요**

**단점:**
- ❌ 무료 티어 제한적 (256MB Postgres)
- ❌ 기능 제한적 (백업, Branching 등 없음)

**추천 대상:**
- 빠르게 시작하고 싶은 경우
- 관리 포인트 최소화 원하는 경우
- DB 크기 256MB 이하인 경우

---

### Option B: Marketplace - Neon + Upstash ⭐⭐⭐⭐⭐ (추천!)

**구성:**
- [Neon Postgres](https://vercel.com/marketplace/neon) (외부 제공자)
- [Upstash Redis](https://vercel.com/marketplace/upstash) (외부 제공자)

**무료 티어:**
| 리소스 | 제한 | Vercel 대비 |
|--------|------|-------------|
| **Neon Postgres** | 512MB 저장소 | **2배 더 넉넉** ✅ |
| Neon 실행 시간 | 191.9시간/월 | **3배 더 넉넉** ✅ |
| Neon Branches | 10개 | DB Branching 지원 ✅ |
| **Upstash Redis** | 256MB | 동일 |
| Upstash 요청 | 10,000/일 | 동일 |

**장점:**
- ✅ **Postgres 2배 저장소** (512MB vs 256MB)
- ✅ **실행 시간 3배** (191.9시간 vs 60시간)
- ✅ **Branching 지원** (DB 복사본 생성 가능)
- ✅ **Auto-Suspend** (5분 미사용 시 자동 정지 → 시간 절약)
- ✅ **Point-in-time Recovery** (시간 여행 백업)
- ✅ **Vercel 대시보드 통합** (환경 변수 자동 주입)

**단점:**
- ❌ Neon 계정 별도 필요 (GitHub 로그인 가능)
- ❌ 관리 포인트 +1 (Vercel + Neon)

**추천 대상:** ⭐
- **대부분의 경우 이 옵션 추천!**
- DB 크기 256MB 초과 우려
- Branching, 백업 등 고급 기능 필요

---

### Option C: Supabase (올인원) ⭐⭐⭐⭐

**구성:**
- [Supabase](https://vercel.com/marketplace/supabase) (Postgres + Auth + Storage + Realtime)
- Upstash Redis (캐싱용)

**무료 티어:**
| 리소스 | 제한 |
|--------|------|
| Postgres 저장소 | 500MB |
| Database Size | 500MB |
| Auth Users | 50,000 MAU |
| File Storage | 1GB |
| Realtime Connections | 200 concurrent |

**장점:**
- ✅ **가장 많은 기능** (Postgres + Auth + Storage + Realtime)
- ✅ **Auth 내장** (JWT 직접 구현 불필요)
- ✅ **Row Level Security** (DB 레벨 권한 관리)
- ✅ **Storage API** (파일 업로드)
- ✅ **Realtime Subscriptions** (DB 변경 실시간 알림)

**단점:**
- ❌ Supabase 계정 필요
- ❌ 기존 FastAPI Auth 코드와 충돌 가능
- ❌ 마이그레이션 복잡 (Auth 시스템 전환 필요)

**추천 대상:**
- 새 프로젝트 시작하는 경우
- Auth, Storage, Realtime 모두 필요한 경우
- 기존 코드 대폭 수정 가능한 경우

---

## 🎯 우리 프로젝트에 적합한 옵션

### 현재 상황:
- DB 크기: ~100MB (여유 있음)
- Auth: FastAPI JWT 이미 구현됨
- Storage: 파일 업로드 사용 안 함
- Realtime: WebSocket 사용 안 함 (폴링 사용)

### 추천 순위:

#### 1순위: Option B - Neon + Upstash ⭐⭐⭐⭐⭐

**이유:**
- ✅ 무료 티어 2배 넉넉 (512MB)
- ✅ Branching 지원 (테스트 DB 복사본)
- ✅ 백업 기능 (Point-in-time Recovery)
- ✅ 기존 코드 변경 최소
- ✅ 설정 10분이면 완료

**설정 방법:**
```
1. Vercel Marketplace → Neon 설치
2. Vercel Marketplace → Upstash 설치
3. 환경 변수 자동 주입 확인
4. 완료!
```

---

#### 2순위: Option A - Vercel Storage ⭐⭐⭐

**이유:**
- ✅ 가장 간단 (Vercel 대시보드만)
- ✅ 계정 추가 불필요
- ⚠️ 256MB 제한 (현재 100MB 사용 중 → 충분)

**설정 방법:**
```
1. Vercel Dashboard → Storage → Postgres 생성
2. Vercel Dashboard → Storage → KV 생성
3. 완료!
```

---

#### 3순위: Option C - Supabase ⭐⭐

**이유:**
- ❌ 기존 FastAPI Auth 코드와 충돌
- ❌ 마이그레이션 복잡
- ❌ 불필요한 기능 많음 (Auth, Storage, Realtime 안 씀)

---

## 📋 최종 추천: Option B (Neon + Upstash)

### 설정 가이드

#### 1단계: Neon Postgres 설치 (5분)

```
1. https://vercel.com/marketplace/neon 접속
2. "Add Integration" 클릭
3. Vercel 계정으로 로그인
4. Project 선택: biz-retriever
5. Neon 계정 생성 (GitHub 로그인 가능)
6. Database 생성:
   - Name: biz-retriever-db
   - Region: AWS us-east-1 (가장 가까운 무료 리전)
7. Install 완료!
```

**자동 생성되는 환경 변수:**
```bash
DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb
POSTGRES_URL=postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb
POSTGRES_PRISMA_URL=...
POSTGRES_URL_NON_POOLING=...
```

---

#### 2단계: Upstash Redis 설치 (3분)

```
1. https://vercel.com/marketplace/upstash 접속
2. "Add Integration" 클릭
3. Project 선택: biz-retriever
4. Upstash 계정 생성
5. Redis Database 생성:
   - Name: biz-retriever-kv
   - Region: AWS us-east-1
6. Install 완료!
```

**자동 생성되는 환경 변수:**
```bash
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=xxx
KV_URL=redis://default:xxx@xxx.upstash.io:6379  # Redis 호환
```

---

#### 3단계: 코드 확인 (이미 완료!)

`app/core/config.py`가 이미 자동 감지하도록 작성됨:

```python
# Neon Postgres URL 자동 감지
if self.POSTGRES_URL:
    url = self.POSTGRES_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

# Upstash Redis URL 자동 감지
if self.KV_URL:
    return self.KV_URL
```

**추가 작업 불필요!** ✅

---

## 🆚 최종 비교표

| 항목 | Vercel Storage | **Neon + Upstash** (추천) | Supabase |
|------|----------------|---------------------------|----------|
| **Postgres 크기** | 256MB | **512MB** ✅ | 500MB |
| **설정 시간** | 5분 | **8분** | 15분 |
| **계정 수** | 1개 | 3개 (Vercel, Neon, Upstash) | 3개 |
| **Branching** | ❌ | ✅ | ✅ |
| **백업** | ❌ | **✅ Point-in-time** | ✅ |
| **코드 변경** | 없음 | **없음** ✅ | 많음 |
| **Auth 충돌** | 없음 | **없음** ✅ | 있음 |
| **무료 티어 여유** | 61% | **80%** ✅ | 80% |

---

## 🎬 다음 단계

### 추천: Option B (Neon + Upstash) 설치

**시작하세요:**
1. https://vercel.com/marketplace/neon
2. https://vercel.com/marketplace/upstash
3. 각각 5분, 3분 소요 (총 8분)
4. 환경 변수 자동 주입됨
5. 완료!

**배포 가이드:** `docs/VERCEL_DEPLOYMENT_FINAL.md` 1단계 수정 필요

---

## ❓ 질문

어떤 옵션을 선택하시겠어요?

**A) Neon + Upstash** (추천 - 무료 티어 2배)  
**B) Vercel Storage** (가장 간단 - 하지만 제한적)  
**C) Supabase** (기능 많음 - 하지만 마이그레이션 복잡)

알려주시면 해당 옵션으로 가이드를 업데이트하겠습니다!
