from fastapi import APIRouter

from app.api.endpoints import (analysis, analytics, auth, bids, crawler,
                               export, filters, keywords, payment, profile,
                               websocket)

api_router = APIRouter()


# Health check endpoint for /api/v1/health
@api_router.get("/health", tags=["health"])
async def api_health_check():
    """
    API Health Check

    /api/v1/health 엔드포인트 - Docker healthcheck 및 모니터링용
    """
    return {"status": "ok", "service": "Biz-Retriever", "version": "1.0.0"}


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(bids.router, prefix="/bids", tags=["bids"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["crawler"])
api_router.include_router(filters.router, prefix="/filters", tags=["filters"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(websocket.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])
api_router.include_router(payment.router, prefix="/payment", tags=["payment"])
