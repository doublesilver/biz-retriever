"""Job schemas for API requests/responses"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Create new job"""

    task_type: str = Field(
        ..., description="Type of task", examples=["gemini_analysis"]
    )
    input_data: Optional[dict] = Field(None, description="Task input parameters")


class JobUpdate(BaseModel):
    """Update job status"""

    status: Optional[str] = Field(None, description="Job status")
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Progress 0-100"
    )
    result: Optional[dict] = Field(None, description="Task result")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class JobResponse(BaseModel):
    """Job response"""

    id: str
    status: str
    task_type: str
    progress: int
    input_data: Optional[dict] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobCreateResponse(BaseModel):
    """Response when creating a new job"""

    job_id: str
    status: str
    message: str
