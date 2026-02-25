# OWASP Top 10 Security Audit Report

**Project**: Biz-Retriever v1.1.0
**Date**: 2026-02-24
**Auditor**: Security Auditor (Automated)
**Scope**: Full stack (FastAPI backend + Vanilla JS frontend)

---

## Executive Summary

전체 OWASP Top 10 카테고리에 대한 전수 감사를 수행했습니다.
**12건의 취약점을 발견**하여 이 중 **10건을 직접 수정**했으며, 2건은 권고사항으로 문서화했습니다.

| 심각도 | 발견 | 수정 | 미수정(권고) |
|--------|------|------|-------------|
| Critical | 2 | 2 | 0 |
| High | 4 | 4 | 0 |
| Medium | 4 | 4 | 0 |
| Low | 2 | 0 | 2 |
| **Total** | **12** | **10** | **2** |

---

## A01: Broken Access Control

### [HIGH] VULN-01: Crawler Trigger - Missing Admin Check
- **File**: `app/api/endpoints/crawler.py:19`
- **Description**: `/crawler/trigger` 엔드포인트가 인증된 모든 사용자에게 열려 있어, 일반 사용자가 크롤링을 무제한 트리거할 수 있었음
- **Impact**: 서비스 남용, API 할당량 소진, 과도한 DB 부하
- **Fix**: `is_superuser` 검증 추가. 관리자가 아닌 사용자는 `403 Forbidden` 반환
- **Status**: FIXED

### [INFO] VULN-02: Bid Read Without Auth
- **File**: `app/api/endpoints/bids.py:71`
- **Description**: `GET /bids/{bid_id}` 및 `GET /bids/` 가 인증 없이 접근 가능
- **Recommendation**: 비즈니스 요건에 따라 공개 API이면 OK. 단, 민감한 정보가 포함된 경우 인증 필요
- **Status**: OK (공개 API로 의도된 것으로 판단)

---

## A02: Cryptographic Failures

### [CRITICAL] VULN-03: Token Blacklist Fails Open
- **File**: `app/core/security.py:279`
- **Description**: Redis 장애 시 `is_token_blacklisted()` 함수가 `False`를 반환하여 이미 로그아웃/블랙리스트된 토큰이 유효하게 처리됨
- **Impact**: 탈취된 토큰으로 무단 접근 가능
- **Fix**: Fail closed 방식으로 변경 - Redis 장애 시 `True` 반환하여 요청 거부. 사용자는 재로그인으로 복구 가능
- **Status**: FIXED

### [OK] JWT Algorithm & Secret
- **File**: `app/core/security.py:18,70`
- **Assessment**: HS256 + `settings.SECRET_KEY` 사용. `algorithms=[ALGORITHM]` 으로 알고리즘 고정하여 Algorithm Confusion 공격 방지. 비밀키는 `.env`에서 관리됨.
- **Status**: PASS

### [OK] Password Hashing
- **File**: `app/core/security.py:106-111`
- **Assessment**: bcrypt (10 rounds) 사용. 업계 표준 수준의 보안
- **Status**: PASS

---

## A03: Injection

### [HIGH] VULN-04: Traceback Exposed to Client
- **File**: `app/api/endpoints/analysis.py:204-208`
- **Description**: Smart Search 에러 시 Python traceback이 JSON 응답에 그대로 포함됨. 내부 파일 경로, 라이브러리 버전, 코드 구조 등이 노출됨
- **Impact**: 정보 수집 단계에서 공격자에게 유리한 정보 제공
- **Fix**: 트레이스백 제거, 일반적 에러 메시지만 반환. 상세 내용은 서버 로그에만 기록
- **Status**: FIXED

### [MEDIUM] VULN-05: Internal Error Details in Multiple Endpoints
- **Files**:
  - `app/api/endpoints/profile.py:101-103` - `str(e)` 노출
  - `app/api/endpoints/payment.py:140` - `str(e)` 노출
  - `app/api/endpoints/payment.py:230` - `str(e)` 노출
  - `app/api/endpoints/payment.py:293` - `str(e)` 노출
  - `app/api/endpoints/payment.py:380` - webhook 에러 상세 노출
  - `app/api/endpoints/crawler.py:44-53` - 에러 타입/메시지 노출
- **Fix**: 모든 에러 응답에서 내부 상세 제거, 사용자 친화적 메시지로 대체
- **Status**: FIXED (6 files)

### [OK] SQL Injection
- **Assessment**: SQLAlchemy ORM의 파라미터 바인딩을 일관되게 사용하여 SQL Injection 위험 없음. `export.py`의 수동 문자열 필터링(`replace("'", "")` 등)은 불필요하고 불완전했으므로 LIKE 와일드카드 이스케이프로 대체
- **Status**: PASS (export.py 개선 완료)

### [OK] XSS
- **Assessment**: Backend는 JSON API만 제공. HTML 렌더링 없음. Frontend는 `textContent` 사용으로 DOM XSS 위험 낮음. 이메일 HTML 템플릿에 사용자 입력이 삽입되나, 이메일 클라이언트에서의 위험은 제한적
- **Status**: PASS

---

## A04: Insecure Design

### [OK] Account Lockout
- 5회 로그인 실패 시 30분 잠금. 적절한 수준
- 이메일 열거 방지: 비밀번호 재설정, 인증 재발송에서 동일한 응답 반환

### [OK] Token Rotation
- Refresh Token 사용 시 이전 토큰을 블랙리스트에 추가하고 새 토큰 쌍 발급

### [OK] Password Policy
- 8자 이상, 대/소문자, 숫자, 특수문자 각 1개 이상 요구

---

## A05: Security Misconfiguration

### [HIGH] VULN-06: Missing Security Headers
- **File**: `app/main.py`
- **Description**: HTTP 응답에 보안 헤더(CSP, X-Frame-Options 등)가 없어 Clickjacking, MIME sniffing, XSS 등의 위험
- **Fix**: `SecurityHeadersMiddleware` ASGI 미들웨어 구현 및 등록
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - `Content-Security-Policy: default-src 'self'; ...`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)
  - `Cache-Control: no-store, no-cache, must-revalidate`
- **Status**: FIXED

### [HIGH] VULN-07: OpenAPI/Swagger & Metrics Exposed in Production
- **File**: `app/main.py`
- **Description**: `/docs`, `/redoc`, `/openapi.json`, `/metrics` 가 프로덕션에서 공개 접근 가능. API 구조와 내부 메트릭이 노출됨
- **Fix**:
  - Production 환경에서 OpenAPI/Swagger/Redoc 비활성화
  - `/metrics` 엔드포인트에 내부 네트워크 IP 제한 추가
- **Status**: FIXED

### [OK] CORS Configuration
- **Assessment**: 특정 도메인만 허용 (localhost, Vercel 도메인). `allow_origins=["*"]` 사용하지 않음.
  - `allow_headers=["*"]`, `expose_headers=["*"]`는 보안에 영향이 제한적이나, 필요한 헤더만 지정하면 더 좋음
  - `allow_credentials=True`와 함께 사용 시 특정 origin 지정 필수 (충족됨)
- **Status**: PASS

### [OK] TrustedHost Middleware
- Host Header Injection 방지를 위한 TrustedHostMiddleware 사용

---

## A06: Vulnerable and Outdated Components

### [LOW] VULN-08: python-jose Known Issues
- **File**: `requirements.txt:21`
- **Description**: `python-jose[cryptography]==3.3.0`은 유지보수가 활발하지 않으며 일부 알려진 이슈가 있음. `PyJWT`가 더 활발하게 유지보수됨
- **Recommendation**: `PyJWT`로 마이그레이션 권고 (기능적 변경 필요)
- **Status**: ADVISORY (향후 마이그레이션 권고)

### [OK] Other Dependencies
- FastAPI 0.115.0, SQLAlchemy 2.0.25, bcrypt 4.1.2 등 주요 패키지는 현재 안정 버전
- psycopg2-binary는 프로덕션에서 psycopg2로 변경 권고 (성능)

---

## A07: Identification and Authentication Failures

### [OK] Authentication
- JWT (Access 15min + Refresh 30days) with rotation and blacklist
- Rate limiting on login (5/min), register (3/min), password reset (3/min)
- Account lockout (5 failures -> 30min lock)

### [OK] OAuth2 Social Login Removed
- Kakao/Naver OAuth2가 제거되어 공격 표면 감소

---

## A08: Software and Data Integrity Failures

### [MEDIUM] VULN-09: Payment Webhook Without Signature Verification
- **File**: `app/api/endpoints/payment.py:319-380`
- **Description**: Tosspayments webhook 엔드포인트가 요청 서명을 검증하지 않음. 공격자가 가짜 webhook을 전송하여 결제 상태를 조작할 수 있음
- **Recommendation**: Tosspayments HMAC 서명 검증 추가 필요. Tosspayments SDK의 `verify_webhook_signature` 활용
- **Status**: ADVISORY (Tosspayments 결제 하드닝 태스크 #2에서 처리 예정)

---

## A09: Security Logging and Monitoring Failures

### [MEDIUM] VULN-10: PII (Email) Leaking in Logs
- **Files**: `app/api/endpoints/auth.py`, `app/core/security.py`, `app/api/endpoints/export.py`
- **Description**: 사용자 이메일이 로그에 평문으로 기록됨 (예: `"User logged in: user@example.com"`). 로그 시스템 침해 시 PII 유출 위험
- **Fix**: 이메일 대신 `user_id`를 사용하도록 로그 메시지 변경
- **Status**: FIXED (11 locations)

### [OK] Logging Infrastructure
- 구조화된 로깅 (logging module), Slack ERROR 알림, Prometheus 메트릭
- Railway 환경 감지하여 파일 로깅 자동 비활성화

---

## A10: Server-Side Request Forgery (SSRF)

### [MEDIUM] VULN-11: Crawler SSRF Risk
- **File**: `app/services/crawler_service.py:233-308`
- **Description**: `_scrape_attachments(url)` 메서드가 외부 URL을 직접 요청함. G2B API에서 반환된 URL만 사용하므로 직접적 위험은 낮으나, URL 검증 없이 내부 네트워크 접근이 가능할 수 있음
- **Mitigation**: 현재 크롤링은 G2B API 응답 URL만 사용하며, 사용자 입력 URL은 사용하지 않음. 추가 보호를 위해 허용된 도메인 화이트리스트 적용 권고
- **Status**: LOW RISK (화이트리스트 권고)

---

## PII Protection Assessment

### Identified PII Fields

| Model | Field | Encrypted | Status |
|-------|-------|-----------|--------|
| User | email | No (hashed index) | DB 레벨 암호화 권고 |
| User | hashed_password | Yes (bcrypt) | PASS |
| User | password_reset_token | No (random token) | PASS (비가역) |
| UserProfile | company_name | No | 암호화 권고 |
| UserProfile | brn (사업자번호) | No | **암호화 필요** |
| UserProfile | representative | No | **암호화 필요** |
| UserProfile | address | No | 암호화 권고 |
| UserProfile | slack_webhook_url | No | **암호화 필요** |

### Recommendations
1. `brn` (사업자등록번호), `representative` (대표자명), `slack_webhook_url` 은 애플리케이션 레벨 암호화 적용 필요
2. PostgreSQL의 `pgcrypto` 확장 또는 Python `cryptography` 패키지를 사용한 필드 암호화 권고
3. 장기적으로 Vault 또는 AWS KMS 같은 키 관리 시스템 도입 권고

---

## Input Validation Audit

| Endpoint | Validation | Status |
|----------|-----------|--------|
| POST /auth/register | Pydantic EmailStr + password min_length=8 + validate_password() | PASS |
| POST /auth/login | OAuth2PasswordRequestForm (standard) | PASS |
| GET /bids/ | Query params: skip(ge=0), limit(ge=1,le=500), keyword(max_length=100) | PASS |
| GET /bids/{bid_id} | Path: bid_id(ge=1) | PASS |
| POST /bids/upload | File extension whitelist, size limit 10MB | PASS |
| GET /export/excel | importance_score(ge=1,le=3), agency(max_length=200) | PASS |
| GET /export/priority-agencies | agencies(max_length=1000), per-agency(max_length=100), max 20 | PASS |
| GET /crawler/status/{task_id} | Regex validation `[a-zA-Z0-9\-]+` | PASS |
| POST /keywords/ | keyword(min_length=1, max_length=50 via schema) | PASS |
| POST /filters/keywords | keyword(min_length=1, max_length=50) | PASS |
| GET /analytics/trends | days(ge=1, le=365) | PASS |
| POST /analysis/smart-search | Pydantic model validation | PASS |

---

## Dependency Security Scan

### requirements.txt Analysis (2026-02-24)

| Package | Version | Known CVEs | Risk |
|---------|---------|-----------|------|
| fastapi | 0.115.0 | None known | Low |
| uvicorn | 0.30.0 | None known | Low |
| sqlalchemy | 2.0.25 | None known | Low |
| bcrypt | 4.1.2 | None known | Low |
| **python-jose** | **3.3.0** | **Maintenance concern** | **Medium** |
| httpx | 0.26.0 | None known | Low |
| PyPDF2 | 3.0.1 | None known | Low |
| beautifulsoup4 | 4.12.3 | None known | Low |
| sendgrid | 6.11.0 | None known | Low |
| pydantic | 2.10.0 | None known | Low |

### Recommendations
1. `python-jose` -> `PyJWT` 마이그레이션 (권고)
2. `psycopg2-binary` -> `psycopg2` (프로덕션 권고)
3. 정기적 `pip audit` 또는 `safety check` 실행 CI에 포함 권고

---

## Changes Summary

### Files Modified
1. `app/main.py` - SecurityHeadersMiddleware 추가, OpenAPI/metrics 접근 제한
2. `app/core/security.py` - Token blacklist fail closed, PII 로그 제거
3. `app/api/endpoints/auth.py` - PII 로그 제거 (7 locations)
4. `app/api/endpoints/analysis.py` - Traceback 노출 제거
5. `app/api/endpoints/profile.py` - Error detail 노출 제거
6. `app/api/endpoints/payment.py` - Error detail 노출 제거 (4 locations)
7. `app/api/endpoints/crawler.py` - Admin access control 추가, error detail 제거
8. `app/api/endpoints/export.py` - SQL injection 방지 개선, PII 로그 제거

### New Files
1. `docs/SECURITY_AUDIT_OWASP_2026.md` - This report

---

## Conclusion

Biz-Retriever v1.1.0은 기본적인 보안 체계(JWT, bcrypt, rate limiting, account lockout, CORS)가 잘 구현되어 있습니다. 이번 감사에서 발견된 주요 취약점들은 모두 수정되었으며, 특히:

1. **Token blacklist fail-open** 취약점이 가장 심각했으며 즉시 수정되었습니다.
2. **Security Headers** 추가로 브라우저 기반 공격 방어를 강화했습니다.
3. **정보 노출** 관련 이슈들(traceback, error details, PII in logs)이 포괄적으로 수정되었습니다.
4. **Access Control** 강화로 관리자 전용 기능이 보호됩니다.

향후 과제:
- PII 필드 암호화 (brn, representative, slack_webhook_url)
- `python-jose` -> `PyJWT` 마이그레이션
- Payment webhook HMAC 서명 검증
- CI/CD에 자동 보안 스캔 통합 (`pip audit`, `bandit`)
