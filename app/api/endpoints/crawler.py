"""
크롤러 API 엔드포인트
수동 크롤링 트리거 및 상태 확인
"""
from fastapi import APIRouter, Depends
from celery.result import AsyncResult
from app.core.security import get_current_user
from app.db.models import User
from app.worker.tasks import crawl_g2b_bids

router = APIRouter()

@router.post("/crawl/trigger")
async def trigger_manual_crawl(current_user: User = Depends(get_current_user)):
    """
    수동 크롤링 트리거 (관리자용)
    
    Returns:
        task_id: Celery task ID
        status: 작업 상태
    """
    task = crawl_g2b_bids.delay()
    return {
        "task_id": task.id,
        "status": "started",
        "message": "G2B 크롤링이 시작되었습니다."
    }

@router.get("/crawl/status/{task_id}")
async def check_crawl_status(task_id: str):
    """
    크롤링 작업 상태 확인
    
    Args:
        task_id: Celery task ID
    
    Returns:
        status: 작업 상태 (PENDING, STARTED, SUCCESS, FAILURE)
        result: 작업 결과 (완료 시)
    """
    task = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None
    }
