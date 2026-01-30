from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class UserKeywordBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="include", pattern="^(include|exclude)$")
    is_active: bool = True

class UserKeywordCreate(UserKeywordBase):
    pass

class UserKeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class UserKeywordResponse(UserKeywordBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserKeywordList(BaseModel):
    items: List[UserKeywordResponse]
