# Changelog

All notable changes to the Biz-Retriever project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-02-24 (In Progress)

### Enterprise Architecture Patterns

#### Added
- **Standard API Response Envelope** (`app/schemas/response.py`):
  - `ApiResponse[T]` 제네릭 래퍼: `{"success": bool, "data": T, "error": ErrorDetail, "meta": ..., "timestamp": ...}`
  - `ok()`, `ok_paginated()`, `fail()` 헬퍼 함수
  - `PaginationMeta` 스키마 (page, per_page, total, total_pages)

- **Structured Exception Hierarchy** (`app/core/exceptions.py`):
  - `BizRetrieverError` 기본 클래스에 `status_code` + `error_code` 내장
  - 4xx: `BadRequestError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `ValidationError`, `RateLimitError`
  - 5xx: `ServiceUnavailableError`, `DatabaseError`
  - Domain-specific: `WeakPasswordError`, `AccountLockedError`, `InvalidTokenError`, `CrawlerError`, `PaymentError`, etc.
  - 도메인별 에러 코드: `AUTH_*`, `BID_*`, `CRAWLER_*`, `PAYMENT_*`

- **Global Exception Handlers** (`app/main.py`):
  - `BizRetrieverError` → 자동 HTTP status + error_code 매핑
  - `RateLimitExceeded` → 통일 포맷 변환
  - `HTTPException` → 레거시 호환 + 통일 포맷
  - `RequestValidationError` → 필드별 에러 구조화
  - Catch-all → Production에서 에러 상세 숨김

- **Architecture Decision Records (ADR)**: CLAUDE.md에 ADR-001~004 기록
  - ADR-001: 표준 API 응답 Envelope
  - ADR-002: 구조화된 에러 계층
  - ADR-003: URL prefix 기반 API 버저닝
  - ADR-004: DDD 레이어 규칙

### Infrastructure — Railway Migration
- **Railway Deployment**: Raspberry Pi → Railway (PostgreSQL + Redis plugins)
- **Dockerfile**: Multi-stage build (builder → runtime → development)
- **start.sh**: All-in-one container (Alembic → Taskiq Worker → Scheduler → Uvicorn)
- **railway.toml**: Health check `/health` (120s timeout), ON_FAILURE restart (max 5)
- **Config**: `DATABASE_URL` / `REDIS_URL` auto-detection for Railway (with `postgres://` → `postgresql+asyncpg://` transform)
- **CORS/TrustedHost**: Dynamic `RAILWAY_PUBLIC_DOMAIN` support

### 🔒 Backend Security Enhancements

#### Added
- **Account Lockout System**:
  - Failed login attempts tracking (5 attempts → 30 minutes lockout)
  - User model fields: `failed_login_attempts`, `locked_until`, `last_login_at`
  - Automatic lockout reset after expiry
  - Remaining attempts notification on failed login

- **Logout Functionality**:
  - New endpoint: `POST /api/v1/auth/logout`
  - Redis-based token blacklist with automatic TTL
  - Token validation in `get_current_user()` checks blacklist
  - Prevents use of logged-out tokens

- **Enhanced Token Security**:
  - Reduced Access Token lifetime: 8 days → **15 minutes** (93% reduction)
  - Refresh Token rotation on `/auth/refresh` (old token blacklisted)
  - Token type validation (prevents using access token as refresh token)

#### Removed
- **OAuth2 Social Login**:
  - Removed Kakao OAuth2 integration
  - Removed Naver OAuth2 integration
  - Simplified to email/password authentication only
  - Reduced attack surface and maintenance complexity

#### Changed
- **Password Policy**: Already strong (8+ chars, uppercase, lowercase, digit, special char) - no changes
- **User Model**: Added security tracking fields (backward compatible)

#### Database
- **New Migration**: `aaab08a12b55_add_user_security_fields.py`
  - Adds `failed_login_attempts` (INTEGER, default 0)
  - Adds `locked_until` (DATETIME, nullable)
  - Adds `last_login_at` (DATETIME, nullable)

### 🖥️ Frontend Security & UX

#### Added
- **Token Refresh Flow** (`api.js`):
  - Login 시 `access_token` + `refresh_token` 모두 localStorage 저장
  - 401 응답 시 자동으로 `/auth/refresh` 호출하여 토큰 갱신
  - 갱신 성공 시 원래 요청 자동 재시도 (`_isRetry` flag)
  - 갱신 실패 시 로그아웃 + 로그인 페이지 리다이렉트
  - **동시 요청 Promise 공유** (`_refreshing` static field): 여러 API 호출이 동시에 401을 받아도 refresh 요청은 1회만 발생

- **Account Lockout UI** (`auth.js`):
  - 계정 잠금 시 실시간 카운트다운 배너 표시
  - `error.isAccountLocked` + `error.lockRemainingMinutes` 구조화된 에러 처리
  - 잠금 해제 시 배너 자동 제거

- **API URL Config 분리** (`config.js`):
  - `window.__CONFIG__` 패턴으로 환경별 API URL 관리
  - Railway 이전 시 `config.js`의 `API_URL`만 변경하면 됨
  - Vite build 시 `import.meta.env.VITE_API_URL` 지원 (TypeScript)

#### Removed
- **Social Login Dead Code**: `loginSNS()` 메서드 제거
- **Duplicate Method Definitions**: License/Performance 메서드 중복 정의 정리

#### Changed
- **에러 메시지 한국어화**: 계정 잠금, 인증 만료 등 사용자 친화적 메시지

---

## [1.0.0] - 2026-01-30

### Infrastructure & Production Readiness

#### Added
- **Celery → Taskiq Migration**: 70% memory reduction (400MB → 120MB)
- **PostgreSQL Optimization**: SD card writes reduced 80%, TPS improved 5x
- **Automatic Backup System**: Daily backups with verification and Slack notifications
- **Monitoring Stack**: Prometheus + Grafana with 11 alert rules
- **HTTPS/SSL**: Let's Encrypt certificates with 6 security headers
- **DDoS Protection**: Nginx 3-layer defense (rate limiting, timeouts, Fail2Ban)
- **JWT Refresh Tokens**: Access Token 15min + Refresh Token 30 days

### Features
- **G2B API Crawler**: Automatic bid data collection (3x daily)
- **AI Analysis**: Google Gemini 2.5 Flash for bid summarization
- **Hard Match Engine**: 3-stage validation (region, license, performance)
- **Price Prediction**: ML-based winning price estimation
- **Slack Notifications**: Real-time alerts for important bids
- **Web Dashboard**: Real-time bid list with analytics
- **Kanban Board**: Bid workflow management
- **Excel Export**: Offline data sharing
- **Subscription System**: Free/Basic/Pro plans with Tosspayments

### Testing
- **164 tests** with **85% coverage**
- E2E tests for critical user flows
- Integration tests for all API endpoints
- Unit tests for business logic

---

## Security Improvements Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Access Token Lifetime** | 8 days | 15 minutes | 99.87% reduction |
| **Brute Force Protection** | None | 5 attempts + lockout | ✅ Protected |
| **Token Revocation** | Not possible | Redis blacklist | ✅ Enabled |
| **OAuth Complexity** | 3 providers | Email only | ✅ Simplified |
| **Login Tracking** | None | Full audit trail | ✅ Implemented |

---

## Migration Guide

### From v1.0.0 to Current

#### 1. Database Migration
```bash
# Run new migration
alembic upgrade head
```

#### 2. Environment Variables
```bash
# Remove from .env (OAuth no longer used):
KAKAO_CLIENT_ID
KAKAO_CLIENT_SECRET
KAKAO_REDIRECT_URI
NAVER_CLIENT_ID
NAVER_CLIENT_SECRET
NAVER_REDIRECT_URI
```

#### 3. Frontend Changes Required
- Remove Kakao/Naver login buttons
- Add logout button with API call to `/api/v1/auth/logout`
- Handle account lockout error messages (show remaining lockout time)
- Update token refresh logic (new tokens returned on refresh)

#### 4. API Changes
**New Endpoints:**
- `POST /api/v1/auth/logout` - Logout and blacklist token

**Modified Endpoints:**
- `POST /api/v1/auth/login/access-token` - Now tracks failed attempts
- `POST /api/v1/auth/refresh` - Now rotates refresh tokens (old token blacklisted)

**Removed Endpoints:**
- `GET /api/v1/auth/login/{provider}` - Social login removed
- `GET /api/v1/auth/callback/{provider}` - Social login callback removed

---

## Breaking Changes

### ⚠️ OAuth2 Social Login Removed
**Impact**: Users who previously logged in with Kakao/Naver cannot login anymore.

**Migration Path**:
1. Contact support to migrate social accounts to email/password
2. Or re-register with email/password (lose previous data)

**Rationale**: 
- Reduced security attack surface
- Simplified authentication flow
- Easier maintenance and compliance
- Focus on core B2B users (email authentication standard)

---

## Known Issues

### Non-Blocking
- Pydantic Field deprecation warnings (cosmetic, will fix in v1.1.0)
- LSP type hints in `security.py` (non-functional, will fix in v1.1.0)

### Fixed in This Release
- ✅ Token blacklist now properly checked on all authenticated requests
- ✅ Database migration for security fields
- ✅ Refresh token rotation working correctly

---

## Upcoming Features (v1.1.0)

- Password reset functionality (email-based)
- Email verification for new accounts
- Batch operations (bulk bid status updates)
- Rate limiting on all endpoints
- Service file consolidation (matching_service.py)
- Database index optimization

---

## Credits

**Developed by**: doublesilver  
**Security Review**: Oracle AI Agent  
**Architecture**: FastAPI + PostgreSQL + Redis + Taskiq  
**AI Provider**: Google Gemini 2.5 Flash  

---

**For deployment instructions, see**: `docs/RAILWAY_DEPLOYMENT.md`
**For architecture review, see**: `docs/ARCHITECTURE_REVIEW_v1.1.0.md`
**For API documentation, visit**: `/docs` (Swagger UI on deployed server)
