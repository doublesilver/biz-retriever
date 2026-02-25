# Biz-Retriever v1.1.0 Architecture Review

**Date**: 2026-02-24
**Reviewer**: Tech Lead Agent
**Scope**: Railway Migration, Security, Refactoring, Test Plan

---

## 1. Railway Migration Architecture Review

### 1.1 Current Architecture (Raspberry Pi)
```
[Vercel Frontend] --> [Tailscale VPN] --> [Raspberry Pi]
                                            |- FastAPI (Uvicorn)
                                            |- Taskiq Worker
                                            |- Taskiq Scheduler
                                            |- PostgreSQL (local)
                                            |- Valkey/Redis (local)
```

### 1.2 Target Architecture (Railway)
```
[Vercel Frontend] --> [Railway Public URL]
                          |
                    [Railway Service]
                     |- FastAPI + Worker + Scheduler (start.sh, single container)
                     |- Railway PostgreSQL (plugin, DATABASE_URL auto)
                     |- Railway Redis (plugin, REDIS_URL auto)
```

### 1.3 Railway Configuration Assessment

**railway.toml** - 현재 상태: 적절함
- `dockerfilePath`: `Dockerfile` (multi-stage build, `runtime` target)
- `healthcheckPath`: `/health` (120s timeout)
- `startCommand`: `bash /app/start.sh`
- `restartPolicyType`: `ON_FAILURE` (max 5 retries)

**start.sh** - 단일 컨테이너 전략 (All-in-One):
- Alembic migration -> Taskiq Worker -> Taskiq Scheduler -> Uvicorn API
- `wait -n` 으로 fail-fast 구현

### 1.4 Railway Migration Issues & Recommendations

#### CRITICAL Issues

| # | Issue | File | Severity |
|---|-------|------|----------|
| 1 | **`get_redis_client` function missing** | `app/core/security.py:236,249,270,272` | **CRITICAL** |
| 2 | **config.py `ACCESS_TOKEN_EXPIRE_MINUTES` still 8 days** | `app/core/config.py:15` | **HIGH** |
| 3 | **.env.example still contains OAuth vars** | `.env.example:57-65` | **MEDIUM** |
| 4 | **rate_limiter.py uses sync `redis.Redis`** | `app/services/rate_limiter.py:24` | **MEDIUM** |
| 5 | **Frontend API_BASE hardcoded to Tailscale** | `frontend/js/api.js:7`, `frontend/src/services/api.ts:13` | **HIGH** |

**Detail: Issue #1 - `get_redis_client` Missing**

`security.py` imports `get_redis_client` from `app.core.cache`, but `cache.py` only defines `get_redis` (async). This is a **runtime error** that will crash token blacklist operations.

```python
# security.py line 236 - BROKEN
from app.core.cache import get_redis_client  # Does not exist!
redis_client = get_redis_client()            # Not awaited!

# cache.py - actual function
async def get_redis() -> aioredis.Redis:     # Different name, async
```

**Fix**: Change `security.py` to `from app.core.cache import get_redis` and `redis_client = await get_redis()`.

**Detail: Issue #2 - Token Expiry Config Mismatch**

`config.py:15` sets `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 8` (8 days), but `security.py:66` hardcodes 15 minutes. The config value is never used. This is confusing and the RAILWAY_DEPLOYMENT.md doc says `ACCESS_TOKEN_EXPIRE_MINUTES=11520` (8 days).

**Fix**: Update `config.py` to `ACCESS_TOKEN_EXPIRE_MINUTES: int = 15` and use it in `create_access_token()`.

**Detail: Issue #5 - Frontend API URL**

Both `api.js` and `api.ts` hardcode `https://leeeunseok.tail32c3e2.ts.net/api/v1`. After Railway migration, this must change to the Railway public domain.

**Fix**: Use environment variable or Vercel environment config for API URL.

#### Railway-Specific Recommendations

1. **DB Connection Pool**: `session.py` pool settings are good (`pool_size=5`, `max_overflow=10`, `pool_recycle=1800`). Railway PostgreSQL supports up to ~97 connections on Hobby plan.

2. **Single Container Tradeoff**: `start.sh` runs API + Worker + Scheduler in one container. This is OK for the current scale but means:
   - No independent scaling of workers
   - One OOM crash kills everything
   - Recommend: Keep this for now (cost efficiency), split later when scaling

3. **PORT Handling**: `start.sh` correctly uses `${PORT:-8000}`. Railway injects `PORT` dynamically.

4. **CORS Origins**: `main.py` dynamically adds `RAILWAY_PUBLIC_DOMAIN` to CORS origins. Good.

5. **TrustedHost**: Wildcard `*.railway.app` and `*.railway.internal` are added when `RAILWAY_PUBLIC_DOMAIN` is set. Good.

---

## 2. v1.1.0 Feature Implementation Direction

### 2.1 Planned Features (from CHANGELOG.md)

| Feature | Priority | Complexity | Backend Dev | Frontend Dev |
|---------|----------|------------|-------------|--------------|
| Password Reset (email) | HIGH | Medium | SendGrid integration + token | Reset form UI |
| Email Verification | MEDIUM | Medium | Verification token flow | Verification page |
| Batch Operations | LOW | Low | Bulk PATCH endpoint | Multi-select UI |
| Rate Limiting (all endpoints) | HIGH | Low | Already partially implemented | N/A |
| Service Consolidation | MEDIUM | Low | Merge match_service + matching_service | N/A |
| DB Index Optimization | MEDIUM | Low | Alembic migration | N/A |

### 2.2 Implementation Recommendations

**Password Reset Flow:**
```
1. POST /auth/forgot-password {email}
   -> Generate reset token (Redis, 15min TTL)
   -> Send email via SendGrid
2. POST /auth/reset-password {token, new_password}
   -> Validate token from Redis
   -> Update password hash
   -> Blacklist all existing tokens for user
```

**Email Verification Flow:**
```
1. POST /auth/register
   -> Set is_active=False (currently True)
   -> Generate verification token
   -> Send verification email
2. GET /auth/verify-email?token=xxx
   -> Validate token
   -> Set is_active=True
```

**Rate Limiting Consolidation:**
- Current: `slowapi` limiter in `main.py` AND custom `RateLimiter` in `rate_limiter.py`
- Recommendation: Use only `slowapi` (already works). Remove custom `RateLimiter` class. Apply `@limiter.limit()` to all endpoints.

---

## 3. Security: Frontend/Backend Consistency Check

### 3.1 Auth Endpoint Mapping

| Backend Endpoint | Frontend (api.js) | Frontend (api.ts) | Status |
|-----------------|-------------------|-------------------|--------|
| `POST /auth/login/access-token` | `API.login()` | `APIService.login()` | OK |
| `POST /auth/register` | `API.register()` | `APIService.register()` | OK |
| `GET /auth/check-email` | `API.checkEmailExists()` | Not implemented | **GAP** |
| `POST /auth/refresh` | Not implemented | Not implemented | **GAP** |
| `POST /auth/logout` | `API.logout()` | Not implemented | **GAP** |
| `GET /auth/users` | Not called | Not implemented | OK (internal) |
| Social Login (removed) | `API.loginSNS()` still exists | N/A | **GAP** |

### 3.2 Critical Gaps

1. **Refresh Token not used by frontend**: Backend issues `refresh_token` on login, but `auth.js:32` only stores `access_token`. The `refresh_token` is discarded. Token auto-refresh on 401 does not exist.

2. **`api.js` still has `loginSNS()` method** (line 132-134): Social login was removed from backend. Dead code.

3. **Token storage**: `auth.js` stores token in `localStorage`. `api.js:logout()` clears both `token` and `refresh_token`, but `refresh_token` was never stored.

4. **api.ts (TypeScript)** is incomplete: Missing `logout()`, `checkEmailExists()`, `refreshToken()`.

5. **api.js has duplicate methods**: `getLicenses`, `addLicense`, `deleteLicense`, `getPerformances`, `addPerformance`, `deletePerformance` are defined twice (lines 276-292 and 349-382).

### 3.3 Recommended Token Flow Fix

```javascript
// Login: Store both tokens
const response = await API.login(email, password);
localStorage.setItem('token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);

// 401 Handler: Auto-refresh before redirect
if (response.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
        const newTokens = await API.refreshToken(refreshToken);
        localStorage.setItem('token', newTokens.access_token);
        localStorage.setItem('refresh_token', newTokens.refresh_token);
        // Retry original request
    } else {
        // No refresh token, redirect to login
        localStorage.clear();
        window.location.href = '/index.html';
    }
}
```

---

## 4. Code Refactoring Recommendations

### 4.1 Service Consolidation

**Problem**: Two matching services with overlapping responsibilities.

| File | Role | Should Keep? |
|------|------|-------------|
| `match_service.py` (303 lines) | HardMatchEngine - region/license/performance | Merge into matching_service |
| `matching_service.py` (241 lines) | MatchingService - hard/soft/semantic match + Gemini | Keep as primary |

**Recommendation**: Merge `HardMatchEngine` from `match_service.py` into `matching_service.py`. The `matching_service.py` already has `check_hard_match()` which duplicates `match_service.py`'s `evaluate()`.

Key difference: `match_service.py` uses `perf.contract_amount` (line 275) while model has `perf.amount` (models.py:277). This is a **bug** in `match_service.py`.

### 4.2 Database Index Optimization

Current indexes (from models.py analysis):

**bid_announcements table:**
- `id` (PK), `title`, `agency`, `source`, `deadline`, `importance_score`, `region_code`, `status` - All have index=True

**Missing indexes for common queries:**
- Composite: `(status, deadline)` - Dashboard sorts by deadline within status
- Composite: `(source, crawled_at)` - Crawler duplicate checking
- Composite: `(assigned_to, status)` - Kanban board per-user filtering

**user_keywords table:**
- Missing: `(user_id, keyword)` unique constraint - prevent duplicate keywords per user

**Alembic migration needed:**
```python
# Recommended indexes
op.create_index('ix_bids_status_deadline', 'bid_announcements', ['status', 'deadline'])
op.create_index('ix_bids_source_crawled', 'bid_announcements', ['source', 'crawled_at'])
op.create_index('ix_bids_assigned_status', 'bid_announcements', ['assigned_to', 'status'])
op.create_index('ix_user_keywords_unique', 'user_keywords', ['user_id', 'keyword'], unique=True)
```

### 4.3 Other Refactoring Items

1. **`datetime.utcnow()` deprecation**: Used throughout (`auth.py`, `security.py`, `models.py`). Should migrate to `datetime.now(UTC)` (Python 3.12+). Not urgent but good practice.

2. **User model OAuth fields**: `provider`, `provider_id` columns still exist in model. Can drop in future migration.

3. **Pydantic v2 deprecation warnings**: `@validator` in `config.py` should become `@field_validator`. Cosmetic but shows in logs.

4. **Duplicate limiter instances**: `main.py:30` creates `Limiter()` and `rate_limiter.py:16` creates another `Limiter()`. The auth endpoints import from `rate_limiter.py` while `main.py` has its own. Should unify.

---

## 5. Integration Test Plan

### 5.1 Test Categories

#### Category A: Auth Flow (Priority: CRITICAL)
```
A1. Register -> Login -> Get Token Pair -> Access Protected Endpoint
A2. Login 5x Wrong -> Account Lock -> Wait/Reset -> Login Success
A3. Login -> Logout -> Reuse Token (should fail)
A4. Login -> Get Refresh Token -> Refresh -> Old Token Blacklisted
A5. Register with weak password -> 400
A6. Register duplicate email -> 400
A7. Rate limiting: 6th login attempt in 1 minute -> 429
```

#### Category B: Railway Infrastructure (Priority: HIGH)
```
B1. Health check endpoints: /health, /api/v1/health
B2. Database connection with DATABASE_URL (Railway format)
B3. Redis connection with REDIS_URL (Railway format)
B4. Alembic migration on startup (idempotent)
B5. CORS: Vercel origin allowed, random origin blocked
B6. TrustedHost: Railway domain accepted
```

#### Category C: Core Business Logic (Priority: HIGH)
```
C1. Crawler trigger -> task queued -> bids saved
C2. Bid CRUD: Create, Read, Update, Delete, List with filters
C3. Kanban: Status transition (new -> reviewing -> bidding -> completed)
C4. Hard Match: Region + License + Performance check
C5. Soft Match: Keyword scoring
C6. AI Analysis: Gemini semantic match (mock in test)
C7. Excel export with filters
C8. Keywords: Add, List, Delete exclude keywords
```

#### Category D: Frontend Integration (Priority: MEDIUM)
```
D1. Login form -> API call -> Token stored -> Dashboard redirect
D2. Dashboard loads bids from API
D3. Kanban drag-drop updates bid status
D4. Export button triggers download
D5. Logout clears token and redirects
```

### 5.2 Test Infrastructure

- **Unit Tests**: pytest + pytest-asyncio (existing 164 tests)
- **Integration Tests**: TestClient + mock DB (existing)
- **E2E Tests**: Existing `test_full_workflow.py`, `test_user_journey.py`
- **Load Tests**: Locust (existing `locustfile.py`)
- **Missing**: Auth flow integration tests (A1-A7) should be added

### 5.3 Test Execution Plan

```
Phase 1: Fix critical bugs (#1 get_redis_client, #5 model attribute bug)
Phase 2: Run existing 164 tests, ensure all pass
Phase 3: Add auth integration tests (A1-A7)
Phase 4: Railway deployment test (B1-B6)
Phase 5: End-to-end with Vercel frontend
```

---

## 6. CLAUDE.md Update Draft

### Changes:
```markdown
## Current State (2026-02-24)

- v1.1.0 development in progress
- Backend: Railway migration (from Raspberry Pi)
- Frontend: Vercel (API URL update needed for Railway)
- Security: JWT refresh token rotation, account lockout implemented
- OAuth2 social login removed (email/password only)
- Tests: 164/164 (100% pass), 85% coverage
- Known Bug: security.py uses nonexistent get_redis_client (fix in progress)

## v1.1.0 Scope

- Railway deployment (PostgreSQL + Redis + API/Worker single container)
- Frontend API URL config for Railway
- Token refresh flow in frontend
- Service consolidation (match_service + matching_service)
- DB index optimization
- Password reset (SendGrid) - stretch goal
```

---

## 7. CHANGELOG.md Update Draft

### [1.1.0] - 2026-02-24 (In Progress)

#### Infrastructure
- **Railway Migration**: Raspberry Pi -> Railway (PostgreSQL + Redis plugins)
- **Dockerfile**: Multi-stage build with runtime target
- **start.sh**: All-in-one container (API + Worker + Scheduler)
- **Health Check**: `/health` endpoint with 120s timeout

#### Security
- Account lockout system (5 attempts -> 30min lock)
- Token blacklist via Redis
- Refresh token rotation
- OAuth2 social login removed
- Rate limiting on auth endpoints

#### Bug Fixes
- Fix `get_redis_client` -> `get_redis` in security.py
- Fix `contract_amount` -> `amount` in match_service.py
- Fix duplicate method definitions in api.js
- Remove dead `loginSNS()` from api.js

#### Frontend
- Store and use refresh_token
- Auto-refresh on 401 before redirect
- Update API_BASE for Railway domain
- Remove social login UI remnants

#### Refactoring
- Consolidate match_service.py into matching_service.py
- Unify rate limiter instances
- Add composite database indexes
- Clean up .env.example (remove OAuth vars)

---

## Summary of Actions for Each Agent

### backend-dev (Task #1)
1. **FIX**: `security.py` - `get_redis_client` -> `get_redis` (await)
2. **FIX**: `config.py` - `ACCESS_TOKEN_EXPIRE_MINUTES` = 15
3. **ADD**: Railway env var support (DATABASE_URL, REDIS_URL auto-detection)
4. **ADD**: Composite DB indexes via Alembic migration
5. **CLEAN**: `.env.example` remove OAuth variables

### frontend-dev (Task #2)
1. **FIX**: Store `refresh_token` on login
2. **ADD**: Auto-refresh token on 401
3. **FIX**: API_BASE -> Railway domain (env config)
4. **REMOVE**: `loginSNS()` dead code
5. **FIX**: Duplicate method definitions in api.js
6. **ADD**: Missing methods in api.ts (logout, checkEmail, refresh)

### qa-engineer (Task #3)
1. **ADD**: Auth integration tests (A1-A7)
2. **VERIFY**: Existing 164 tests pass
3. **ADD**: Token blacklist test
4. **ADD**: Rate limiting test
5. **REVIEW**: match_service.py `contract_amount` bug
