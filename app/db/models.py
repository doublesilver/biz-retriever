from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from typing import List as ListType


class BidAnnouncement(Base, TimestampMixin):
    """
    Model for Bid Announcements (입찰 공고)
    Biz-Retriever Phase 1: 크롤링 및 자동 필터링 지원
    """
    __tablename__ = "bid_announcements"

    # 기본 필드
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full text content
    agency: Mapped[Optional[str]] = mapped_column(String, index=True)  # Ordering Agency
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # Original Link
    processed: Mapped[bool] = mapped_column(Boolean, default=False)  # RAG Processing Status

    # Phase 1 추가 필드
    source: Mapped[str] = mapped_column(String, index=True, default="G2B")  # "G2B", "Onbid", etc.
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)  # 마감일시
    estimated_price: Mapped[Optional[float]] = mapped_column(Float)  # 추정가 (원)
    importance_score: Mapped[int] = mapped_column(Integer, default=1, index=True)  # 1~3 (별점)
    keywords_matched: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)  # 매칭된 키워드 목록
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)  # Slack 알림 여부
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 크롤링 시간

    # Phase 2 추가 필드 (Kanban 상태 관리)
    status: Mapped[str] = mapped_column(String, default="new", index=True)  # new, reviewing, bidding, completed
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )  # 담당자
    notes: Mapped[Optional[str]] = mapped_column(Text)  # 메모

    # Relationship: BidAnnouncement -> User (담당자)
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_bids",
        foreign_keys=[assigned_to],
        lazy="selectin"  # Async 지원을 위한 eager loading
    )

    def __repr__(self):
        return f"<BidAnnouncement(id={self.id}, title='{self.title}')>"


class User(Base, TimestampMixin):
    """
    User Model (사용자)
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship: User -> BidAnnouncement (담당 공고 목록)
    assigned_bids: Mapped[List["BidAnnouncement"]] = relationship(
        "BidAnnouncement",
        back_populates="assignee",
        lazy="selectin"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
