from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class UserBasicInfo(BaseModel):
    """간단한 사용자 정보 (담당자 표시용)"""
    id: int
    email: str

    class Config:
        from_attributes = True


class BidBase(BaseModel):
    """공고 기본 스키마"""
    title: str = Field(..., min_length=1, max_length=500, description="공고 제목")
    content: str = Field(..., min_length=1, description="공고 내용")
    agency: Optional[str] = Field(default=None, max_length=200, description="기관명")
    posted_at: datetime = Field(..., description="게시일시")
    url: str = Field(..., description="원본 URL")


class BidCreate(BidBase):
    """공고 생성 스키마"""
    pass


class BidUpdate(BaseModel):
    """공고 수정 스키마"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    content: Optional[str] = Field(default=None, min_length=1)
    agency: Optional[str] = Field(default=None, max_length=200)
    posted_at: Optional[datetime] = None
    url: Optional[str] = None
    processed: Optional[bool] = None
    status: Optional[str] = Field(default=None, pattern="^(new|reviewing|bidding|submitted|won|lost|completed)$")
    assigned_to: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = None


class BidResponse(BidBase):
    """공고 응답 스키마 (전체 필드)"""
    id: int
    created_at: datetime
    updated_at: datetime
    processed: bool

    # Phase 1 필드
    source: str = "G2B"
    deadline: Optional[datetime] = None
    estimated_price: Optional[float] = None
    importance_score: int = 1
    keywords_matched: Optional[List[str]] = None
    is_notified: bool = False
    ai_summary: Optional[str] = None
    ai_keywords: Optional[List[str]] = None

    # Phase 2 필드
    status: str = "new"
    assigned_to: Optional[int] = None
    notes: Optional[str] = None

    # 담당자 정보 (relationship)
    assignee: Optional[UserBasicInfo] = None

    class Config:
        from_attributes = True


class BidAnnouncementCreate(BaseModel):
    """크롤러용 공고 생성 스키마 (내부용)"""
    title: str
    content: str
    agency: Optional[str] = None
    posted_at: datetime
    url: str
    source: str = "G2B"
    deadline: Optional[datetime] = None
    estimated_price: Optional[float] = None
    importance_score: int = 1
    keywords_matched: Optional[List[str]] = None


class BidAssignRequest(BaseModel):
    """공고 담당자 할당 요청"""
    user_id: Optional[int] = Field(None, ge=1, description="담당자 ID (None이면 할당 해제)")


class BidStatusUpdate(BaseModel):
    """공고 상태 변경 요청"""
    status: str = Field(..., pattern="^(new|reviewing|bidding|submitted|won|lost|completed)$", description="공고 상태")
    notes: Optional[str] = Field(default=None, max_length=1000, description="메모")


class BidListResponse(BaseModel):
    """공고 목록 응답 스키마 (페이지네이션 지원)"""
    items: List[BidResponse]
    total: int
    skip: int
    limit: int
