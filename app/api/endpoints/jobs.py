"""Job status endpoints for async task polling"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.job import JobResponse
from app.services.job_service import JobService

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Get job status by ID.

    Client polls this endpoint to check async task progress.

    Returns:
    - **id**: Job UUID
    - **status**: PENDING | PROCESSING | SUCCESS | FAILURE | CANCELLED
    - **progress**: 0-100 percentage
    - **result**: Task result (when SUCCESS)
    - **error_message**: Error details (when FAILURE)

    Polling interval recommendation: 2 seconds
    """
    job = await JobService.get_job(db, job_id, current_user.id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job
