import asyncio
import os
import sys
import time
import uuid

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Windows에서 asyncpg 호환성을 위한 EventLoop 정책 변경
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


import structlog

from app.api.api import api_router
from app.core.config import settings
from app.core.exceptions import BizRetrieverError
from app.core.logging import logger
from app.core.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
    init_app_info,
)
from app.core.sentry import init_sentry
from app.schemas.response import fail

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)


# ============================================
# Security Headers 미들웨어
# ============================================
class SecurityHeadersMiddleware:
    """
    OWASP 권장 보안 헤더를 모든 응답에 추가하는 ASGI 미들웨어

    추가되는 헤더:
    - X-Content-Type-Options: MIME sniffing 방지
    - X-Frame-Options: Clickjacking 방지
    - X-XSS-Protection: 구형 브라우저 XSS 필터 활성화
    - Referrer-Policy: Referrer 정보 누출 방지
    - Permissions-Policy: 브라우저 기능 제한
    - Content-Security-Policy: XSS/데이터 주입 공격 방지
    - Strict-Transport-Security: HTTPS 강제 (프로덕션)
    - Cache-Control: 민감한 데이터 캐시 방지
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                security_headers = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",
                    ),
                    (b"cache-control", b"no-store, no-cache, must-revalidate"),
                    (b"pragma", b"no-cache"),
                ]
                # HSTS only in production
                if os.getenv("ENVIRONMENT", "development") == "production":
                    security_headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                existing = list(message.get("headers", []))
                existing.extend(security_headers)
                message["headers"] = existing
            await send(message)

        await self.app(scope, receive, send_with_headers)


# ============================================
# Prometheus 메트릭 미들웨어
# ============================================
class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    HTTP 요청/응답 메트릭을 자동으로 수집하는 미들웨어
    """

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        # 메트릭 엔드포인트 제외
        if path in ["/metrics", "/health"]:
            return await call_next(request)

        # 요청마다 고유 request_id 생성 및 structlog 컨텍스트 바인딩
        # 이 ID가 모든 로그에 자동으로 포함되어 요청 추적이 가능
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=method,
            path=path,
        )

        # CORS Preflight 요청 로깅
        if method == "OPTIONS":
            origin = request.headers.get("origin", "no-origin")
            logger.info("cors_preflight", origin=origin)
            return await call_next(request)

        logger.info("request_started")

        # 진행 중 요청 카운터 증가
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # 요청 완료 메트릭 기록
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status_code=str(status_code)).inc()

            return response
        except Exception:
            # 에러 발생 시 500으로 기록
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status_code="500").inc()
            raise
        finally:
            # 처리 시간 기록
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(duration)

            # 진행 중 요청 카운터 감소
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()


tags_metadata = [
    {
        "name": "auth",
        "description": "인증 관련 API (로그인, 회원가입)",
    },
    {
        "name": "bids",
        "description": "입찰 공고 CRUD 및 검색 API",
    },
    {
        "name": "analytics",
        "description": "통계 분석 및 대시보드 API",
    },
    {
        "name": "export",
        "description": "엑셀 내보내기 API (narajangteo 방식)",
    },
    {
        "name": "crawler",
        "description": "크롤링 작업 관리 API (Celery 연동)",
    },
    {
        "name": "filters",
        "description": "제외 키워드 필터 관리 API",
    },
    {
        "name": "analysis",
        "description": "AI 기반 투찰가 예측 API",
    },
]

# Production에서 OpenAPI/Swagger 비활성화 (A05: Security Misconfiguration)
_is_production = os.getenv("ENVIRONMENT", "development") == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=None if _is_production else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    description="""
# Biz-Retriever API

공공 입찰 정보 자동 수집 및 AI 분석 시스템입니다.

## 주요 기능

* **입찰 공고 자동 수집** - G2B, 온비드 크롤링
* **AI 기반 분석** - 중요도 평가, 투찰가 예측
* **실시간 알림** - Slack 웹훅 연동
* **엑셀 내보내기** - narajangteo 방식 지원

## 인증

Bearer Token 방식의 JWT 인증을 사용합니다.
`Authorization: Bearer <token>` 헤더를 포함하세요.
    """,
    version="1.1.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Biz-Retriever Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)


# Rate Limiting State
app.state.limiter = limiter


# ============================================
# Global Exception Handlers (Enterprise Pattern)
#
# 우선순위: BizRetrieverError → RateLimitExceeded → HTTPException
#           → RequestValidationError → Exception (catch-all)
#
# 모든 에러 응답은 통일된 ApiResponse envelope 포맷:
# {"success": false, "error": {"code": "...", "message": "..."}, "timestamp": "..."}
# ============================================


@app.exception_handler(BizRetrieverError)
async def biz_error_handler(request: Request, exc: BizRetrieverError):
    """
    도메인 예외 처리 — BizRetrieverError 계층의 모든 예외를 자동으로
    해당 HTTP 상태 코드 + 구조화된 에러 코드로 변환.
    """
    logger.warning(f"[{exc.error_code}] {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(
            code=exc.error_code,
            message=exc.detail,
            details=exc.extra if not _is_production else None,
            path=str(request.url.path),
        ),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Rate limit 초과 — 통일 포맷으로 변환"""
    logger.warning(f"Rate Limit Exceeded: {request.url.path}")
    return JSONResponse(
        status_code=429,
        content=fail(
            code="RATE_LIMIT_EXCEEDED",
            message="요청 제한을 초과했습니다. 잠시 후 다시 시도하세요.",
            path=str(request.url.path),
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    FastAPI HTTPException 처리 — 기존 raise HTTPException 코드와 호환.
    """
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            path=str(request.url.path),
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 유효성 검사 오류 — 필드별 에러 목록을 details에 포함.
    """
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({"field": field, "message": message})

    logger.warning(f"Validation Error: {errors} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=fail(
            code="VALIDATION_ERROR",
            message="입력값 검증에 실패했습니다.",
            details=errors,
            path=str(request.url.path),
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all 예외 처리 — 예상치 못한 서버 오류.
    프로덕션에서는 에러 상세를 숨기고, 개발 환경에서는 노출.
    """
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
    )

    details = None
    if not _is_production:
        details = {"exception": type(exc).__name__, "message": str(exc)}

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=fail(
            code="INTERNAL_ERROR",
            message="서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            details=details,
            path=str(request.url.path),
        ),
    )


# Security Headers 미들웨어 등록 (OWASP A05: Security Headers)
app.add_middleware(SecurityHeadersMiddleware)

# Prometheus 메트릭 미들웨어 등록 (먼저 등록 - 역순 실행됨)
app.add_middleware(PrometheusMiddleware)

# 동적 CORS origins 빌드
cors_origins = list(settings.CORS_ORIGINS)
if settings.RAILWAY_PUBLIC_DOMAIN:
    cors_origins.append(f"https://{settings.RAILWAY_PUBLIC_DOMAIN}")
if settings.PRODUCTION_DOMAIN:
    cors_origins.append(f"https://{settings.PRODUCTION_DOMAIN}")

# CORS 설정 - FastAPI 공식 CORSMiddleware 사용
# IMPORTANT: CORS must be added AFTER other middlewares (executed FIRST in reverse order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows OPTIONS for preflight
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# 동적 TrustedHost 목록 빌드
allowed_hosts = [
    "localhost",
    "127.0.0.1",
    "test",  # For pytest integration tests
    "testserver",  # For TestClient
    "biz-retriever.vercel.app",
    "biz-retriever-doublesilvers-projects.vercel.app",
    "biz-retriever-git-master-doublesilvers-projects.vercel.app",
]
if settings.RAILWAY_PUBLIC_DOMAIN:
    allowed_hosts.append(settings.RAILWAY_PUBLIC_DOMAIN)
    # Railway reverse proxy handles host validation, allow internal probe hosts
    allowed_hosts.extend(["*.railway.app", "*.railway.internal"])
if settings.PRODUCTION_DOMAIN:
    allowed_hosts.append(settings.PRODUCTION_DOMAIN)
if settings.ALLOWED_HOSTS:
    allowed_hosts.extend(h.strip() for h in settings.ALLOWED_HOSTS.split(",") if h.strip())

# TrustedHost 미들웨어 - Host 헤더 검증 (Host Header Injection 공격 방지)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)

# API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Note: Static files are served by nginx (frontend container)
# No app.mount("/static", ...) needed for API-only service

# from fastapi_cache import FastAPICache  # Removed due to dependency conflict
# from fastapi_cache.backends.redis import RedisBackend
# from redis import asyncio as aioredis


@app.on_event("startup")
async def startup():
    """애플리케이션 시작 시 초기화"""
    logger.info("application_starting")

    try:
        # Sentry Error Tracking 초기화
        init_sentry()
        logger.info("sentry_initialized")

        # Prometheus 메트릭 초기화
        init_app_info(version="1.1.0")
        logger.info("prometheus_initialized")

        # DB Tables Init
        from app.db.base import Base
        from app.db.session import engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        logger.info("database_initialized")

        # Taskiq Init (Celery 대체)
        from app.worker.taskiq_app import startup as taskiq_startup

        await taskiq_startup()
        logger.info("taskiq_initialized")

        logger.info("application_startup_complete")
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown():
    """애플리케이션 종료 시 정리"""
    logger.info("application_shutting_down")

    # Taskiq Cleanup
    from app.worker.taskiq_app import shutdown as taskiq_shutdown

    await taskiq_shutdown()
    logger.info("taskiq_stopped")


# Force reload for CORS update


@app.get("/")
async def read_root():
    """API 루트 - 서비스 정보 반환"""
    return {
        "service": "Biz-Pass API",
        "version": "1.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
@limiter.limit("60/minute")  # Rate limiting: 분당 60회
async def health_check(request: Request):
    """
    Health Check API

    서버 상태 확인용 엔드포인트
    """
    return {"status": "ok", "service": "Biz-Retriever", "version": "1.1.0"}


@app.get("/metrics")
async def metrics(request: Request):
    """
    Prometheus 메트릭 엔드포인트

    Prometheus 서버에서 스크래핑하여 메트릭을 수집합니다.
    Grafana 대시보드와 연동하여 모니터링할 수 있습니다.

    반환 형식: text/plain (Prometheus exposition format)

    보안: Production 환경에서는 내부 네트워크만 접근 허용
    """
    # Production에서 메트릭 접근 제한 (A05: Security Misconfiguration)
    if _is_production:
        client_host = request.client.host if request.client else "unknown"
        allowed_ranges = (
            "127.0.0.1",
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",
            "::1",
        )
        if not any(client_host.startswith(r) for r in allowed_ranges):
            raise HTTPException(status_code=404, detail="Not found")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
