import asyncio
import os
import sys
import time

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# Windows에서 asyncpg 호환성을 위한 EventLoop 정책 변경
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from app.api.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import (HTTP_REQUEST_DURATION_SECONDS,
                              HTTP_REQUESTS_IN_PROGRESS, HTTP_REQUESTS_TOTAL,
                              init_app_info)

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)


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

        # DEBUG: Request Start
        logger.info(f"INCOMING REQUEST: {method} {path}")

        # 진행 중 요청 카운터 증가
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # 요청 완료 메트릭 기록
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=path, status_code=str(status_code)
            ).inc()

            return response
        except Exception as e:
            # 에러 발생 시 500으로 기록
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=path, status_code="500"
            ).inc()
            raise
        finally:
            # 처리 시간 기록
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(
                duration
            )

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

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
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
    version="1.0.0",
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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================
# Global Exception Handlers
# ============================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 예외 처리 - 사용자 친화적 메시지 반환
    """
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    요청 검증 실패 처리 - Pydantic 유효성 검사 오류
    """
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")

    error_message = "; ".join(errors)
    logger.warning(f"Validation Error: {error_message} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "message": "입력값 검증에 실패했습니다",
            "details": errors,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    일반 예외 처리 - 예상치 못한 서버 오류
    """
    # 개발 환경에서는 상세 오류 로그, 프로덕션에서는 제한적 정보
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
    )

    # 프로덕션 환경에서는 상세 에러 정보를 숨김
    if os.getenv("ENVIRONMENT", "development") == "production":
        error_detail = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    else:
        error_detail = f"{type(exc).__name__}: {str(exc)}"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": error_detail,
            "path": str(request.url.path),
        },
    )


# CORS 설정 - 허용 도메인 구성 (가장 먼저 등록 - 미들웨어는 역순 실행)
cors_origins = settings.CORS_ORIGINS

if settings.PRODUCTION_DOMAIN:
    cors_origins.append(settings.PRODUCTION_DOMAIN)

# Local Test Frontend
cors_origins.append("http://localhost:8081")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["*"],  # 모든 응답 헤더 노출
    max_age=600,  # preflight 캐시 10분
)

# Prometheus 메트릭 미들웨어 등록
app.add_middleware(PrometheusMiddleware)

# TrustedHost 미들웨어 - Host 헤더 검증 (Host Header Injection 공격 방지)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "leeeunseok.tail32c3e2.ts.net",
        "biz-retriever.vercel.app",  # Vercel 프론트엔드
        "biz-retriever-doublesilvers-projects.vercel.app",  # Vercel 자동 도메인
        "biz-retriever-git-master-doublesilvers-projects.vercel.app",  # Vercel 브랜치
        "localhost",
        "127.0.0.1",
        "test",  # For pytest integration tests
        "testserver",  # For TestClient
    ],
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
    logger.info("🚀 Starting Biz-Retriever application...")

    try:
        # Prometheus 메트릭 초기화
        init_app_info(version="1.0.0")
        logger.info("✅ Prometheus metrics initialized")

        # Redis Cache Init (Removed - TODO: Implement manual Redis caching)
        # redis = aioredis.from_url(settings.REDIS_URL)
        # FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info("✅ Redis cache initialized")

        # DB Tables Init
        from app.db.base import Base
        from app.db.session import engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")

        # Taskiq Init (Celery 대체)
        from app.worker.taskiq_app import startup as taskiq_startup

        await taskiq_startup()
        logger.info("✅ Taskiq worker initialized")

        logger.info("🎉 Application startup complete!")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """애플리케이션 종료 시 정리"""
    logger.info("👋 Shutting down Biz-Retriever...")

    # Taskiq Cleanup
    from app.worker.taskiq_app import shutdown as taskiq_shutdown

    await taskiq_shutdown()
    logger.info("✅ Taskiq worker stopped")


# Force reload for CORS update


@app.get("/")
async def read_root():
    """API 루트 - 서비스 정보 반환"""
    return {
        "service": "Biz-Pass API",
        "version": "1.0.0",
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
    return {"status": "ok", "service": "Biz-Retriever", "version": "1.0.0"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 엔드포인트

    Prometheus 서버에서 스크래핑하여 메트릭을 수집합니다.
    Grafana 대시보드와 연동하여 모니터링할 수 있습니다.

    반환 형식: text/plain (Prometheus exposition format)
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
