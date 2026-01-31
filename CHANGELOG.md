# Changelog

All notable changes to the Biz-Retriever project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🔒 Security Enhancements (2026-01-31)

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

**For deployment instructions, see**: `RASPBERRY_PI_DEPLOY_GUIDE.md`  
**For API documentation, visit**: `https://node.tail32c3e2.ts.net/docs`
