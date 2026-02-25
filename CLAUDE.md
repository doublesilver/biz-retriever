# CLAUDE.md - 프로젝트 지침

## 응답 규칙

모든 작업(코드 변경, 기능 추가, 버그 수정, 리팩토링 등)에 반드시 **학습 노트**를 포함한다.

### 학습 노트 구성

**1. 개념 설명**
- 적용하는 기술이 무엇인지, 왜 필요한지, 어떻게 동작하는지
- 비개발자(제로베이스)도 이해할 수 있는 비유와 실생활 예시 사용
- 핵심 키워드 정리

**2. 코드 설명**
- 변경 전/후 비교
- 주요 코드 라인이 하는 역할을 한 줄씩 설명

**3. 결과 정리**
- 적용 후 달라진 점
- 체감 가능한 차이 (성능, 보안, UX 등)

### 주의사항
- 기술 난이도는 실무/포트폴리오 수준으로 높게 유지
- 설명은 처음 접하는 사람도 따라올 수 있게 쉽게 작성
- 한국어로 작성

## 프로젝트 개요

- **서비스**: 입찰 공고 자동 수집 + Gemini AI 분석 시스템
- **Stack**: FastAPI (Async) + SQLAlchemy 2.0 + PostgreSQL + Valkey + Taskiq
- **Frontend**: Vanilla JS SPA (Vercel 배포) — https://biz-retriever.vercel.app
- **Backend**: Raspberry Pi + Tailscale (Railway 이전 예정)
- **AI**: Google Gemini 2.5 Flash + LangChain
- **Tests**: 164/164 (100% pass), 85% coverage

## 핵심 경로

```
app/                  # FastAPI 백엔드
  api/endpoints/      # REST API (auth, bids, analytics, export)
  core/               # config, security, exceptions, database
  schemas/response.py # 표준 API 응답 래퍼 (ApiResponse, ok, fail)
  services/           # crawler, rag, notification
  worker/             # Taskiq tasks & scheduler
frontend/             # Vanilla JS SPA (Vercel)
tests/                # unit + integration + e2e
docs/                 # 운영 가이드 (14개)
monitoring/           # Prometheus + Grafana
```

## 아키텍처 결정 기록 (ADR)

### ADR-001: 표준 API 응답 Envelope (v1.1.0)
- **결정**: 모든 API 응답을 `{"success": bool, "data": ..., "error": ..., "timestamp": ...}` envelope로 통일
- **이유**: 프론트엔드에서 일관된 에러/성공 처리, API 소비자 DX 향상
- **구현**: `app/schemas/response.py` — `ok()`, `ok_paginated()`, `fail()` 헬퍼
- **마이그레이션**: 기존 엔드포인트는 점진적 전환. 새 엔드포인트는 반드시 사용

### ADR-002: 구조화된 에러 계층 (v1.1.0)
- **결정**: `BizRetrieverError` 기본 클래스에 `status_code` + `error_code` 내장
- **이유**: `raise HTTPException` 대신 `raise NotFoundError("bid", 123)` — 도메인 표현력 강화
- **구현**: `app/core/exceptions.py` — 계층: BizRetrieverError → BadRequestError/NotFoundError/... → WeakPasswordError/CrawlerError/...
- **글로벌 핸들러**: `main.py`의 `biz_error_handler`가 자동으로 HTTP 상태 코드 + error_code 매핑
- **에러 코드 체계**: `AUTH_*`, `BID_*`, `CRAWLER_*`, `PAYMENT_*` 도메인별 prefix

### ADR-003: API 버저닝 전략 (v1.1.0)
- **결정**: URL prefix 기반 (`/api/v1/...`), 기존 유지
- **이유**: 명시적, REST 표준, 프록시/캐시 친화적
- **확장**: v2 추가 시 `api_v2_router`를 `main.py`에서 `/api/v2` prefix로 마운트

### ADR-004: DDD 레이어 규칙 (v1.1.0)
- **규칙**: API → Service → Repository 단방향 의존
- **API 레이어**: HTTP 관련 처리만 (요청 파싱, 응답 직렬화)
- **Service 레이어**: 비즈니스 로직 (여러 Repository 조합, 외부 API 호출)
- **Repository 레이어**: 데이터 접근만 (SQLAlchemy 쿼리)
- **예외**: auth 엔드포인트는 보안 민감성으로 인해 Service 없이 직접 DB 접근 허용

## 현재 상태 — v1.1.0 엔터프라이즈 고도화 진행중 (2026-02-24)

### 완료
- 불필요 문서 49개 삭제, README 리팩토링
- Backend 보안 강화: JWT refresh token rotation, 계정 잠금(5회 실패 → 30분), 토큰 블랙리스트
- OAuth2 소셜 로그인 제거 (Kakao/Naver) → email/password only
- Frontend 보안 적용: token refresh 자동 갱신, 계정 잠금 UI, API URL config 분리
- Railway 배포 설정: Dockerfile (multi-stage), railway.toml, start.sh
- DB migration: 사용자 보안 필드 추가 (`failed_login_attempts`, `locked_until`, `last_login_at`)
- **엔터프라이즈 패턴**: 표준 API 응답 래퍼, 에러 계층 구조, 글로벌 에러 핸들링

### 진행중
- Railway 실제 배포 및 연동 테스트
- Backend 버그 수정 (`security.py` Redis 클라이언트 함수명 불일치)
- 코드 품질 개선 및 테스트 보강
- 서비스 통합 (match_service + matching_service)
- DB 복합 인덱스 추가
- 엔터프라이즈 고도화 (결제 하드닝, CI/CD, 보안 감사, 디자인 시스템)

### 남은 작업 (v1.1.0 범위)
- Frontend API URL을 Railway 도메인으로 전환 (config.js 수정)
- Password reset (SendGrid) — stretch goal
- Email verification — stretch goal

## 코딩 컨벤션

### 에러 발생
```python
# Good: 도메인 예외 사용 (자동 HTTP 매핑)
from app.core.exceptions import NotFoundError, BadRequestError
raise NotFoundError("공고", bid_id)
raise BadRequestError("유효하지 않은 플랜입니다.")

# Avoid: HTTPException 직접 사용 (레거시 허용하지만 신규 코드에서 지양)
raise HTTPException(status_code=404, detail="Not found")
```

### API 응답
```python
# Good: 표준 래퍼 사용
from app.schemas.response import ok, ok_paginated
return ok({"id": 1, "name": "test"})
return ok_paginated(items, total=250, skip=0, limit=20)

# Avoid: dict 직접 반환 (레거시 허용)
return {"items": [...], "total": 100}
```

## 개발 환경

- Windows 11, bash shell
- Python 3.11+
- `cd "C:/Users/korea/biz-retriever"` 형식 사용
