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

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="입찰 정보 자동 수집 및 AI 분석 시스템",
    version="1.0.0"
)

# Rate Limiting State
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:3000", 
        "https://your-production-domain.com"  # 실제 도메인으로 변경
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        redis = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")
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
