"""
Vercel Serverless entry point for Biz-Retriever FastAPI app

This file adapts the full production app for Vercel's serverless environment:
- Removes Taskiq (uses Vercel Cron instead)
- Removes Prometheus (uses Vercel Analytics instead)
- Converts startup/shutdown to lifespan pattern
- Maintains all API functionality
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette import status

# Windows에서 asyncpg 호환성을 위한 EventLoop 정책 변경
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import API router and settings
from app.api.api import api_router
from app.core.config import settings
from app.core.logging import logger

# Rate Limiter 설정
limiter = Limiter(key_func=get_remote_address)


# ============================================
# Lifespan Context Manager (replaces @app.on_event)
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - startup and shutdown logic
    
    This replaces the deprecated @app.on_event("startup") and @app.on_event("shutdown")
    decorators with the modern lifespan pattern.
    
    NOTE for Vercel:
    - Startup runs on every cold start (~1-2s for Python)
    - Shutdown has max 500ms limit
    - Taskiq NOT initialized (use Vercel Cron Jobs instead)
    - Prometheus NOT initialized (use Vercel Analytics instead)
    """
    # ============ STARTUP ============
    logger.info("🚀 Starting Biz-Retriever on Vercel Serverless...")
    
    # Initialize database tables (if needed)
    # Note: Migrations should be run separately, not on every cold start
    try:
        from app.db.base import Base
        from app.db.session import engine
        
        async with engine.begin() as conn:
            # In production, use Alembic migrations
            # This is for development/testing only
            if os.getenv("VERCEL_ENV") != "production":
                await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    # NOTE: Taskiq worker NOT initialized (use Vercel Cron Jobs instead)
    # NOTE: Prometheus NOT initialized (use Vercel Analytics instead)
    
    logger.info("🎉 Application startup complete!")
    
    yield  # Application runs here
    
    # ============ SHUTDOWN ============
    # Shutdown (max 500ms on Vercel)
    logger.info("👋 Shutting down Biz-Retriever...")
    try:
        from app.db.session import engine
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ============================================
# OpenAPI Tags Metadata
# ============================================
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
        "description": "크롤링 작업 관리 API (Vercel Cron 연동)",
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


# ============================================
# Create FastAPI App
# ============================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="""
# Biz-Retriever API (Vercel Serverless)

입찰 정보 자동 수집 및 AI 분석 시스템

## Features
- JWT 인증
- Google Gemini AI 분석
- Server-Sent Events (SSE) 실시간 알림
- Job+Polling 비동기 작업

## Serverless Adaptations
- Taskiq → Vercel Cron Jobs
- Prometheus → Vercel Analytics
- Max execution time: 60s (Pro: 300s)
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
    lifespan=lifespan,  # Use lifespan instead of @app.on_event
)


# ============================================
# Rate Limiting State
# ============================================
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
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)} - Path: {request.url.path}",
        exc_info=True,
    )

    # 프로덕션 환경에서는 상세 에러 정보를 숨김
    vercel_env = os.getenv("VERCEL_ENV", "development")
    if vercel_env == "production":
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


# ============================================
# Middleware Configuration
# ============================================

# CORS 설정 - MUST be added LAST to be executed FIRST in reverse order
# Vercel domains + local development + preview deployments
cors_origins = [
    "https://biz-retriever.vercel.app",  # Vercel Production
    "https://biz-retriever-doublesilvers-projects.vercel.app",  # Vercel Auto Domain
    "https://biz-retriever-git-master-doublesilvers-projects.vercel.app",  # Vercel Branch
    "https://leeeunseok.tail32c3e2.ts.net",  # Tailscale (self-hosted backend)
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:8000",
]

# Add any additional origins from settings
for origin in settings.CORS_ORIGINS:
    if origin not in cors_origins:
        cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows OPTIONS for preflight
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# TrustedHost 미들웨어 - Host 헤더 검증 (Host Header Injection 공격 방지)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "*.vercel.app",  # All Vercel deployments
        "biz-retriever.vercel.app",
        "biz-retriever-doublesilvers-projects.vercel.app",
        "biz-retriever-git-master-doublesilvers-projects.vercel.app",
        "leeeunseok.tail32c3e2.ts.net",
        "localhost",
        "127.0.0.1",
        "test",  # For pytest integration tests
        "testserver",  # For TestClient
    ],
)


# ============================================
# API Router
# ============================================
app.include_router(api_router, prefix=settings.API_V1_STR)


# ============================================
# Root Endpoints
# ============================================
@app.get("/")
async def read_root():
    """API 루트 - 서비스 정보 반환"""
    return {
        "service": "Biz-Retriever API",
        "version": "1.0.0",
        "platform": "Vercel Serverless",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health",
    }


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
        "version": "1.0.0",
        "platform": "vercel",
    }


# ============================================
# Vercel Handler (ASGI)
# ============================================
handler = app
