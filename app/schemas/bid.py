from datetime import datetime

from pydantic import BaseModel, Field


class UserBasicInfo(BaseModel):
    """간단한 사용자 정보 (담당자 표시용)"""

    id: int
    email: str

    model_config = {"from_attributes": True}


class BidBase(BaseModel):
    """공고 기본 스키마"""

    title: str = Field(..., min_length=1, max_length=500, description="공고 제목")
    content: str = Field(..., min_length=1, description="공고 내용")
    agency: str | None = Field(default=None, max_length=200, description="기관명")
    posted_at: datetime = Field(..., description="게시일시")
    url: str = Field(..., description="원본 URL")


class BidCreate(BidBase):
    """공고 생성 스키마"""

    pass


class BidUpdate(BaseModel):
    """공고 수정 스키마"""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    agency: str | None = Field(default=None, max_length=200)
    posted_at: datetime | None = None
    url: str | None = None
    processed: bool | None = None
    status: str | None = Field(default=None, pattern="^(new|reviewing|bidding|submitted|won|lost|completed)$")
    assigned_to: int | None = Field(default=None, ge=1)
    notes: str | None = None


class BidResponse(BidBase):
    """공고 응답 스키마 (전체 필드)"""

    id: int
    created_at: datetime
    updated_at: datetime
    processed: bool

    # Phase 1 필드
    source: str = "G2B"
    deadline: datetime | None = None
    estimated_price: float | None = None
    importance_score: int = 1
    keywords_matched: list[str] | None = None
    is_notified: bool = False
    ai_summary: str | None = None
    ai_keywords: list[str] | None = None

    # Phase 2 필드
    status: str = "new"
    assigned_to: int | None = None
    notes: str | None = None

    # 담당자 정보 (relationship)
    assignee: UserBasicInfo | None = None

    model_config = {"from_attributes": True}


class BidAnnouncementCreate(BaseModel):
    """크롤러용 공고 생성 스키마 (내부용)"""

    title: str
    content: str
    agency: str | None = None
    posted_at: datetime
    url: str
    source: str = "G2B"
    deadline: datetime | None = None
    estimated_price: float | None = None
    importance_score: int = 1
    keywords_matched: list[str] | None = None


class BidAssignRequest(BaseModel):
    """공고 담당자 할당 요청"""

    user_id: int | None = Field(None, ge=1, description="담당자 ID (None이면 할당 해제)")


class BidStatusUpdate(BaseModel):
    """공고 상태 변경 요청"""

    status: str = Field(
        ...,
        pattern="^(new|reviewing|bidding|submitted|won|lost|completed)$",
        description="공고 상태",
    )
    notes: str | None = Field(default=None, max_length=1000, description="메모")


class BidListResponse(BaseModel):
    """공고 목록 응답 스키마 (페이지네이션 지원)"""

    items: list[BidResponse]
    total: int
    skip: int
    limit: int
