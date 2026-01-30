"""
크롤러 API 엔드포인트
수동 크롤링 트리거 및 상태 확인 (Taskiq)
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api import deps
from app.core.logging import logger

router = APIRouter()


@router.post("/trigger")
async def trigger_manual_crawl(current_user: deps.CurrentUser):
    """
    수동 크롤링 트리거 (관리자용)

    Returns:
        task_id: Taskiq task ID
        status: 작업 상태
    """
    logger.info(f"수동 크롤링 트리거: user={current_user.email}")

    try:
        # Taskiq 태스크 import
        from app.worker.taskiq_tasks import crawl_g2b_bids

        logger.info("Taskiq 태스크 호출 시도...")
        result = await crawl_g2b_bids.kiq()
        logger.info(f"Taskiq 태스크 생성 완료: task_id={result.task_id}")

        return {
            "task_id": result.task_id,
            "status": "started",
            "message": "G2B 크롤링이 시작되었습니다.",
        }

    except ImportError as e:
        logger.error(f"Taskiq 태스크 임포트 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"크롤링 모듈을 로드할 수 없습니다. (원인: {str(e)})",
        )
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"크롤링 트리거 실패 [{error_type}]: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"크롤링 서비스를 시작할 수 없습니다. ({error_type}: {str(e)})",
        )


@router.get("/status/{task_id}")
async def check_crawl_status(
    task_id: str = Path(..., min_length=1, max_length=100, description="Taskiq Task ID")
):
    """
    크롤링 작업 상태 확인

    - **task_id**: Taskiq task ID (영문자, 숫자, 하이픈만 허용)

    Returns:
        status: 작업 상태 정보
        note: Taskiq는 작업 상태를 Redis에 직접 조회하거나 별도 저장 로직이 필요
    """
    # Task ID 형식 검증
    if not re.match(r"^[a-zA-Z0-9\-]+$", task_id):
        raise HTTPException(
            status_code=400,
            detail="Task ID는 영문자, 숫자, 하이픈만 포함할 수 있습니다.",
        )

    # Taskiq는 Celery의 AsyncResult 같은 기본 상태 조회 메커니즘이 없음
    # Redis에서 직접 조회하거나, DB에 상태를 저장하는 방식으로 구현 필요
    # 현재는 기본 응답만 반환
    return {
        "task_id": task_id,
        "status": "unknown",
        "message": "Taskiq 작업 상태 조회는 별도 구현이 필요합니다. Redis 또는 DB에서 상태를 저장/조회하는 로직을 추가하세요.",
        "note": "크롤링 결과는 DB의 BidAnnouncement 테이블을 확인하세요.",
    }
