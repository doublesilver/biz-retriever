from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class UserLicenseBase(BaseModel):
    license_name: str
    license_number: Optional[str] = None
    issue_date: Optional[datetime] = None


class UserLicenseCreate(UserLicenseBase):
    pass


class UserLicenseUpdate(BaseModel):
    license_name: Optional[str] = None
    license_number: Optional[str] = None
    issue_date: Optional[datetime] = None


class UserLicenseResponse(UserLicenseBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPerformanceBase(BaseModel):
    project_name: str
    amount: float
    completion_date: Optional[datetime] = None


class UserPerformanceCreate(UserPerformanceBase):
    pass


class UserPerformanceUpdate(BaseModel):
    project_name: Optional[str] = None
    amount: Optional[float] = None
    completion_date: Optional[datetime] = None


class UserPerformanceResponse(UserPerformanceBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileBase(BaseModel):
    company_name: Optional[str] = None
    brn: Optional[str] = None
    representative: Optional[str] = None
    address: Optional[str] = None
    location_code: Optional[str] = None
    company_type: Optional[str] = None

    # Notification Settings (WBS-3.3)
    slack_webhook_url: Optional[str] = None
    is_email_enabled: Optional[bool] = False
    is_slack_enabled: Optional[bool] = False

    # Detailed Profile
    credit_rating: Optional[str] = None
    employee_count: Optional[int] = None
    founding_year: Optional[int] = None
    main_bank: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    licenses: List[UserLicenseBase] = []
    performances: List[UserPerformanceBase] = []

    model_config = {"from_attributes": True}
