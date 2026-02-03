"""Job service for managing async tasks (Job+Polling pattern)"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Job
from app.schemas.job import JobCreate, JobUpdate


class JobService:
    """Service for Job+Polling pattern"""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        user_id: int,
        job_data: JobCreate,
    ) -> Job:
        """Create a new job"""
        job = Job(
            id=str(uuid4()),
            user_id=user_id,
            task_type=job_data.task_type,
            input_data=job_data.input_data,
            status="PENDING",
            progress=0,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        logger.info(f"Created job {job.id} ({job.task_type}) for user {user_id}")
        return job

    @staticmethod
    async def get_job(
        db: AsyncSession, job_id: str, user_id: int
    ) -> Optional[Job]:
        """Get job by ID (user-scoped)"""
        result = await db.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_job_by_id(db: AsyncSession, job_id: str) -> Optional[Job]:
        """Get job by ID (no user scoping - for internal use)"""
        result = await db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_job(
        db: AsyncSession,
        job_id: str,
        update_data: JobUpdate,
    ) -> Optional[Job]:
        """Update job status/progress/result"""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None

        if update_data.status:
            job.status = update_data.status
            if update_data.status == "PROCESSING" and not job.started_at:
                job.started_at = datetime.utcnow()
            elif update_data.status in ["SUCCESS", "FAILURE", "CANCELLED"]:
                job.completed_at = datetime.utcnow()

        if update_data.progress is not None:
            job.progress = update_data.progress
        if update_data.result is not None:
            job.result = update_data.result
        if update_data.error_message is not None:
            job.error_message = update_data.error_message

        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def mark_processing(db: AsyncSession, job_id: str) -> Optional[Job]:
        """Mark job as processing"""
        return await JobService.update_job(
            db, job_id, JobUpdate(status="PROCESSING")
        )

    @staticmethod
    async def mark_success(
        db: AsyncSession, job_id: str, result: dict
    ) -> Optional[Job]:
        """Mark job as successful with result"""
        return await JobService.update_job(
            db, job_id, JobUpdate(status="SUCCESS", progress=100, result=result)
        )

    @staticmethod
    async def mark_failure(
        db: AsyncSession, job_id: str, error_message: str
    ) -> Optional[Job]:
        """Mark job as failed with error message"""
        return await JobService.update_job(
            db, job_id, JobUpdate(status="FAILURE", error_message=error_message)
        )

    @staticmethod
    async def update_progress(
        db: AsyncSession, job_id: str, progress: int
    ) -> Optional[Job]:
        """Update job progress (0-100)"""
        return await JobService.update_job(
            db, job_id, JobUpdate(progress=progress)
        )


# Singleton instance
job_service = JobService()
