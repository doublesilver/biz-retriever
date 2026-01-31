from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text)
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
    url: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )  # Original Link
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # RAG Processing Status
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)  # AI 요약
    ai_keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # AI 추출 키워드

    # Phase 1 추가 필드
    source: Mapped[str] = mapped_column(
        String, index=True, default="G2B"
    )  # "G2B", "Onbid", etc.
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime, index=True
    )  # 마감일시
    estimated_price: Mapped[Optional[float]] = mapped_column(Float)  # 추정가 (원)
    importance_score: Mapped[int] = mapped_column(
        Integer, default=1, index=True
    )  # 1~3 (별점)
    keywords_matched: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # 매칭된 키워드 목록
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)  # Slack 알림 여부
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )  # 크롤링 시간
    attachment_content: Mapped[Optional[str]] = mapped_column(
        Text
    )  # OCR/Parsed content from HWP/PDF

    # Phase 3: Hard Match용 제약 조건
    region_code: Mapped[Optional[str]] = mapped_column(
        String, index=True
    )  # 공사 현장 지역 코드 (서울: 11 등)
    min_performance: Mapped[Optional[float]] = mapped_column(
        Float, default=0.0
    )  # 최소 실적 요건(금액)
    license_requirements: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # 필요 면허 목록

    # Phase 2 추가 필드 (Kanban 상태 관리)
    status: Mapped[str] = mapped_column(
        String, default="new", index=True
    )  # new, reviewing, bidding, completed
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # 담당자
    notes: Mapped[Optional[str]] = mapped_column(Text)  # 메모

    # Relationship: BidAnnouncement -> User (담당자)
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_bids",
        foreign_keys=[assigned_to],
        lazy="selectin",  # Async 지원을 위한 eager loading
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
    
    # Security & Login Management
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)  # 로그인 실패 횟수
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 계정 잠금 해제 시간
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 마지막 로그인 시간
    
    # OAuth2 Fields (Deprecated - kept for backward compatibility)
    provider: Mapped[str] = mapped_column(
        String, default="email"
    )  # email (OAuth removed)
    provider_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Deprecated
    profile_image: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Profile Image URL
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    full_profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    assigned_bids: Mapped[List["BidAnnouncement"]] = relationship(
        back_populates="assignee", cascade="all, delete-orphan", lazy="selectin"
    )

    # Billing Relationships (Phase 3)
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[List["PaymentHistory"]] = relationship(
        "PaymentHistory", back_populates="user", lazy="selectin"
    )
    keywords: Mapped[List["UserKeyword"]] = relationship(
        "UserKeyword",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class UserProfile(Base, TimestampMixin):
    """
    User Profile Model (기업 상세 정보)
    Phase 2: 사용자 프로필 자동화 및 정밀 매칭의 기초
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # 기업 기본 정보
    company_name: Mapped[Optional[str]] = mapped_column(
        String, index=True
    )  # 상호/법인명
    brn: Mapped[Optional[str]] = mapped_column(
        String, unique=True, index=True
    )  # 사업자등록번호
    representative: Mapped[Optional[str]] = mapped_column(String)  # 대표자명
    address: Mapped[Optional[str]] = mapped_column(String)  # 본사 주소
    location_code: Mapped[Optional[str]] = mapped_column(
        String, index=True
    )  # 지역 코드 (서울: 11 등)
    company_type: Mapped[Optional[str]] = mapped_column(
        String
    )  # 기업 구분 (중소기업, 소상공인 등)
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # 관심 키워드 (Phase 3 Soft Match)

    # Phase 6.1: Detailed Profile
    credit_rating: Mapped[Optional[str]] = mapped_column(
        String
    )  # 신용등급 (e.g. "A-", "BBB+")
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)  # 직원 수
    founding_year: Mapped[Optional[int]] = mapped_column(Integer)  # 설립연도
    main_bank: Mapped[Optional[str]] = mapped_column(String)  # 주거래 은행
    standard_industry_codes: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # 표준산업분류코드

    # Phase 8: Notification Settings
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Slack Webhook URL
    is_email_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # 이메일 알림 사용 여부
    is_slack_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # Slack 알림 사용 여부

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="full_profile")
    licenses: Mapped[List["UserLicense"]] = relationship(
        "UserLicense",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    performances: Mapped[List["UserPerformance"]] = relationship(
        "UserPerformance",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<UserProfile(id={self.id}, company_name='{self.company_name}')>"


class UserLicense(Base, TimestampMixin):
    """
    User License Model (보유 면허 정보)
    Phase 3: Hard Match (면허 제한) 필터링에 사용
    """

    __tablename__ = "user_licenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )

    license_name: Mapped[str] = mapped_column(
        String, index=True, nullable=False
    )  # 면허명
    license_number: Mapped[Optional[str]] = mapped_column(String)  # 면허번호
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 취득일

    # Relationship
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="licenses"
    )

    def __repr__(self):
        return f"<UserLicense(id={self.id}, name='{self.license_name}')>"


class UserPerformance(Base, TimestampMixin):
    """
    User Performance Model (시공/용역 실적 정보)
    Phase 3: Hard Match (실적 제한) 필터링에 사용
    """

    __tablename__ = "user_performances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )

    project_name: Mapped[str] = mapped_column(String, nullable=False)  # 프로젝트명
    amount: Mapped[float] = mapped_column(Float, default=0.0)  # 계약금액
    completion_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 준공일

    # Relationship
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="performances"
    )

    def __repr__(self):
        return f"<UserPerformance(id={self.id}, project='{self.project_name}', amount={self.amount})>"


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
        index=True,
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
    winning_rate: Mapped[Optional[float]] = mapped_column(
        Float
    )  # 낙찰률 (낙찰가/추정가 * 100)

    # 입찰 참여 정보
    participant_count: Mapped[Optional[int]] = mapped_column(Integer)  # 참여업체 수
    bid_method: Mapped[Optional[str]] = mapped_column(
        String
    )  # 입찰방식 (전자입찰, 협상계약 등)

    # 일시 정보
    bid_open_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, index=True
    )  # 개찰일시
    contract_date: Mapped[Optional[datetime]] = mapped_column(DateTime)  # 계약일

    # 카테고리 (ML 학습용)
    category: Mapped[Optional[str]] = mapped_column(
        String, index=True
    )  # 공사, 용역, 물품 등
    sub_category: Mapped[Optional[str]] = mapped_column(String)  # 세부 카테고리
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON, default=list
    )  # 관련 키워드

    # 메타데이터
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)  # 원본 API 응답 데이터

    # Relationship
    bid_announcement: Mapped[Optional["BidAnnouncement"]] = relationship(
        "BidAnnouncement", foreign_keys=[bid_announcement_id], lazy="selectin"
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
    task_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True
    )  # Celery task ID
    status: Mapped[str] = mapped_column(
        String, index=True
    )  # started, completed, failed

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


class UserKeyword(Base, TimestampMixin):
    """
    User Keyword Model (Dynamic Targeting)
    Phase 3: 사용자 정의 키워드 (Hardcode Replacement)
    """

    __tablename__ = "user_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    keyword: Mapped[str] = mapped_column(String, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String, default="include")  # include, exclude
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="keywords")

    def __repr__(self):
        return f"<UserKeyword(id={self.id}, user_id={self.user_id}, keyword='{self.keyword}')>"


class Subscription(Base, TimestampMixin):
    """
    Subscription Model (구독 관리)
    Phase 3: Billing System
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    plan_name: Mapped[str] = mapped_column(String, default="free")  # free, basic, pro
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_billing_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Stripe/Payment Gateway IDs
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, index=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="subscription")


class PaymentHistory(Base, TimestampMixin):
    """
    Payment History Model (결제 이력)
    """

    __tablename__ = "payment_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="KRW")
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, paid, failed, refunded
    payment_method: Mapped[str] = mapped_column(String, default="card")
    transaction_id: Mapped[Optional[str]] = mapped_column(String, index=True)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="payments")
