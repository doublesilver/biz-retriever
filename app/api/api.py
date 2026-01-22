from fastapi import APIRouter
from app.api.endpoints import bids, auth, crawler, filters, analysis, export, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(bids.router, prefix="/bids", tags=["bids"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["crawler"])
api_router.include_router(filters.router, prefix="/filters", tags=["filters"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
