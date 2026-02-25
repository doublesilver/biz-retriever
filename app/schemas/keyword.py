from datetime import datetime

from pydantic import BaseModel, Field


class UserKeywordBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="include", pattern="^(include|exclude)$")
    is_active: bool = True


class UserKeywordCreate(UserKeywordBase):
    pass


class UserKeywordUpdate(BaseModel):
    keyword: str | None = None
    category: str | None = None
    is_active: bool | None = None


class UserKeywordResponse(UserKeywordBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserKeywordList(BaseModel):
    items: list[UserKeywordResponse]
