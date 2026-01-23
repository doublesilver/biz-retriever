from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

from app.core.config import settings
from app.core.logging import logger
from app.api.api import api_router

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)

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
