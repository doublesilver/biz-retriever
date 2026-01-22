from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl

class BidBase(BaseModel):
    title: str
    content: str
    agency: Optional[str] = None
    posted_at: datetime
    url: str

class BidCreate(BidBase):
    pass

class BidUpdate(BidBase):
    title: Optional[str] = None
    content: Optional[str] = None
    posted_at: Optional[datetime] = None
    url: Optional[str] = None
    processed: Optional[bool] = None

class BidResponse(BidBase):
    id: int
    created_at: datetime
    updated_at: datetime
    processed: bool

    class Config:
        from_attributes = True
