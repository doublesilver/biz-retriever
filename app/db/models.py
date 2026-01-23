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


class BidResult(Base, TimestampMixin):
    """
    낙찰 결과 모델
    입찰 공고의 낙찰 결과를 저장하여 ML 모델 학습에 활용
    """
    __tablename__ = "bid_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 원본 공고 연결
    bid_announcement_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("bid_announcements.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # 공고 기본 정보 (공고가 삭제되어도 결과는 보존)
    bid_number: Mapped[str] = mapped_column(String, unique=True, index=True)  # 입찰번호
    title: Mapped[str] = mapped_column(String, index=True)
    agency: Mapped[Optional[str]] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, default="G2B", index=True)

    # 낙찰 정보
    winning_company: Mapped[str] = mapped_column(String, index=True)  # 낙찰업체명
    winning_price: Mapped[float] = mapped_column(Float, index=True)  # 낙찰금액
    base_price: Mapped[Optional[float]] = mapped_column(Float)  # 기초금액
    estimated_price: Mapped[Optional[float]] = mapped_column(Float)  # 추정가
    winning_rate: Mapped[Optional[float]] = mapped_column(Float)  # 낙찰률 (낙찰가/추정가 * 100)

    # 입찰 참여 정보
    participant_count: Mapped[Optional[int]] = mapped_column(Integer)  # 참여업체 수
    bid_method: Mapped[Optional[str]] = mapped_column(String)  # 입찰방식 (전자입찰, 협상계약 등)

    # 일시 정보
    bid_open_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)  # 개찰일시
    contract_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 계약일

    # 카테고리 (ML 학습용)
    category: Mapped[Optional[str]] = mapped_column(String, index=True)  # 공사, 용역, 물품 등
    sub_category: Mapped[Optional[str]] = mapped_column(String)  # 세부 카테고리
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)  # 관련 키워드

    # 메타데이터
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)  # 원본 API 응답 데이터

    # Relationship
    bid_announcement: Mapped[Optional["BidAnnouncement"]] = relationship(
        "BidAnnouncement",
        foreign_keys=[bid_announcement_id],
        lazy="selectin"
    )

    def __repr__(self):
        return f"<BidResult(id={self.id}, bid_number='{self.bid_number}', winning_price={self.winning_price})>"

    @property
    def winning_rate_calculated(self) -> Optional[float]:
        """낙찰률 계산 (낙찰가/추정가 * 100)"""
        if self.estimated_price and self.estimated_price > 0:
            return round((self.winning_price / self.estimated_price) * 100, 2)
        return None


class CrawlerLog(Base, TimestampMixin):
    """
    크롤러 실행 로그
    크롤링 히스토리 및 통계 추적
    """
    __tablename__ = "crawler_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 크롤링 정보
    source: Mapped[str] = mapped_column(String, index=True)  # G2B, Onbid
    task_id: Mapped[Optional[str]] = mapped_column(String, unique=True)  # Celery task ID
    status: Mapped[str] = mapped_column(String, index=True)  # started, completed, failed

    # 실행 통계
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    # 결과 통계
    total_fetched: Mapped[int] = mapped_column(Integer, default=0)  # 총 수집 건수
    total_filtered: Mapped[int] = mapped_column(Integer, default=0)  # 필터링 통과 건수
    total_new: Mapped[int] = mapped_column(Integer, default=0)  # 신규 저장 건수
    total_duplicate: Mapped[int] = mapped_column(Integer, default=0)  # 중복 건수

    # 에러 정보
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text)

    # 검색 조건
    search_params: Mapped[Optional[dict]] = mapped_column(JSON)  # 검색 파라미터

    def __repr__(self):
        return f"<CrawlerLog(id={self.id}, source='{self.source}', status='{self.status}')>"

    @property
    def success_rate(self) -> Optional[float]:
        """성공률 계산"""
        if self.total_fetched > 0:
            return round((self.total_new / self.total_fetched) * 100, 2)
        return None


class ExcludeKeyword(Base, TimestampMixin):
    """
    제외 키워드 모델
    크롤링 필터링 시 사용되는 제외어 관리
    """
    __tablename__ = "exclude_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    def __repr__(self):
        return f"<ExcludeKeyword(id={self.id}, word='{self.word}')>"
