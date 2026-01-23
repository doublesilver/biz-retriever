from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os
import time

from app.core.config import settings
from app.core.logging import logger
from app.api.api import api_router
from app.core.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    init_app_info,
)

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

        # 진행 중 요청 카운터 증가
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # 요청 완료 메트릭 기록
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=path,
                status_code=str(status_code)
            ).inc()

            return response
        except Exception as e:
            # 에러 발생 시 500으로 기록
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=path,
                status_code="500"
            ).inc()
            raise
        finally:
            # 처리 시간 기록
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=path
            ).observe(duration)

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

# Prometheus 메트릭 미들웨어 등록
app.add_middleware(PrometheusMiddleware)

# CORS 설정 - 허용 도메인 구성
cors_origins = list(settings.CORS_ORIGINS)
if settings.PRODUCTION_DOMAIN:
    cors_origins.append(settings.PRODUCTION_DOMAIN)

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
    max_age=600,  # preflight 캐시 10분
)

# API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    """애플리케이션 시작 시 초기화"""
    logger.info("🚀 Starting Biz-Retriever application...")

    try:
        # Prometheus 메트릭 초기화
        init_app_info(version="1.0.0")
        logger.info("✅ Prometheus metrics initialized")

        # Redis Cache Init
        redis = aioredis.from_url(settings.REDIS_URL)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
        logger.info("✅ Redis cache initialized")
        
        # DB Tables Init
        from app.db.base import Base
        from app.db.session import engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")
        
        logger.info("🎉 Application startup complete!")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    """애플리케이션 종료 시 정리"""
    logger.info("👋 Shutting down Biz-Retriever...")

# Force reload for CORS update

@app.get("/")
async def read_root():
    """메인 페이지"""
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/health")
@limiter.limit("60/minute")  # Rate limiting: 분당 60회
async def health_check(request: Request):
    """
    Health Check API

    서버 상태 확인용 엔드포인트
    """
    return {
        "status": "ok",
        "service": "Biz-Retriever",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 엔드포인트

    Prometheus 서버에서 스크래핑하여 메트릭을 수집합니다.
    Grafana 대시보드와 연동하여 모니터링할 수 있습니다.

    반환 형식: text/plain (Prometheus exposition format)
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
