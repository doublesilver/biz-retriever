from datetime import datetime

from pydantic import BaseModel


class UserLicenseBase(BaseModel):
    license_name: str
    license_number: str | None = None
    issue_date: datetime | None = None


class UserLicenseCreate(UserLicenseBase):
    pass


class UserLicenseUpdate(BaseModel):
    license_name: str | None = None
    license_number: str | None = None
    issue_date: datetime | None = None


class UserLicenseResponse(UserLicenseBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPerformanceBase(BaseModel):
    project_name: str
    amount: float
    completion_date: datetime | None = None


class UserPerformanceCreate(UserPerformanceBase):
    pass


class UserPerformanceUpdate(BaseModel):
    project_name: str | None = None
    amount: float | None = None
    completion_date: datetime | None = None


class UserPerformanceResponse(UserPerformanceBase):
    id: int
    profile_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileBase(BaseModel):
    company_name: str | None = None
    brn: str | None = None
    representative: str | None = None
    address: str | None = None
    location_code: str | None = None
    company_type: str | None = None

    # Notification Settings (WBS-3.3)
    slack_webhook_url: str | None = None
    is_email_enabled: bool | None = False
    is_slack_enabled: bool | None = False

    # Detailed Profile
    credit_rating: str | None = None
    employee_count: int | None = None
    founding_year: int | None = None
    main_bank: str | None = None


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    licenses: list[UserLicenseBase] = []
    performances: list[UserPerformanceBase] = []

    model_config = {"from_attributes": True}
