"""
크롤러 API 엔드포인트
수동 크롤링 트리거 및 상태 확인
"""
import re
from fastapi import APIRouter, Depends, HTTPException, Path
from celery.result import AsyncResult
from app.core.security import get_current_user
from app.core.logging import logger
from app.db.models import User
from app.worker.tasks import crawl_g2b_bids

router = APIRouter()


@router.post("/trigger")
async def trigger_manual_crawl(current_user: User = Depends(get_current_user)):
    """
    수동 크롤링 트리거 (관리자용)

    Returns:
        task_id: Celery task ID
        status: 작업 상태
    """
    logger.info(f"수동 크롤링 트리거: user={current_user.email}")

    task = crawl_g2b_bids.delay()

    return {
        "task_id": task.id,
        "status": "started",
        "message": "G2B 크롤링이 시작되었습니다."
    }


@router.get("/status/{task_id}")
async def check_crawl_status(
    task_id: str = Path(
        ...,
        min_length=1,
        max_length=100,
        description="Celery Task ID"
    )
):
    """
    크롤링 작업 상태 확인

    - **task_id**: Celery task ID (영문자, 숫자, 하이픈만 허용)

    Returns:
        status: 작업 상태 (PENDING, STARTED, SUCCESS, FAILURE)
        result: 작업 결과 (완료 시)
    """
    # Task ID 형식 검증
    if not re.match(r'^[a-zA-Z0-9\-]+$', task_id):
        raise HTTPException(
            status_code=400,
            detail="Task ID는 영문자, 숫자, 하이픈만 포함할 수 있습니다."
        )

    task = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None
    }
