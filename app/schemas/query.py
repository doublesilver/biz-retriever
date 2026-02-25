"""
쿼리 파라미터 검증 스키마
API 엔드포인트의 입력 검증을 위한 Pydantic 모델
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BidSource(str, Enum):
    """입찰 공고 출처"""

    G2B = "G2B"
    ONBID = "Onbid"


class BidStatus(str, Enum):
    """입찰 공고 상태"""

    NEW = "new"
    REVIEWING = "reviewing"
    BIDDING = "bidding"
    COMPLETED = "completed"


class SortOrder(str, Enum):
    """정렬 순서"""

    ASC = "asc"
    DESC = "desc"


# ===========================================
# GET /bids 쿼리 파라미터
# ===========================================
class BidsQueryParams(BaseModel):
    """공고 목록 조회 쿼리 파라미터"""

    skip: int = Field(default=0, ge=0, description="건너뛸 개수")
    limit: int = Field(default=100, ge=1, le=500, description="조회 개수 (최대 500)")
    keyword: str | None = Field(default=None, min_length=1, max_length=100, description="검색 키워드")
    agency: str | None = Field(default=None, min_length=1, max_length=200, description="기관명")
    source: BidSource | None = Field(default=None, description="출처 필터 (G2B, Onbid)")
    status: BidStatus | None = Field(default=None, description="상태 필터")
    importance_score: int | None = Field(default=None, ge=1, le=3, description="중요도 (1-3)")

    @field_validator("keyword")
    @classmethod
    def sanitize_keyword(cls, v: str | None) -> str | None:
        """키워드에서 위험한 문자 제거"""
        if v:
            # SQL Injection 방지를 위한 특수문자 제거
            return v.replace("'", "").replace('"', "").replace(";", "").strip()
        return v


# ===========================================
# GET /export/excel 쿼리 파라미터
# ===========================================
class ExcelExportParams(BaseModel):
    """엑셀 내보내기 쿼리 파라미터"""

    importance_score: int | None = Field(default=None, ge=1, le=3, description="중요도 필터 (1-3)")
    source: BidSource | None = Field(default=None, description="출처 필터")
    agency: str | None = Field(default=None, min_length=1, max_length=200, description="기관명 필터")


# ===========================================
# GET /export/priority-agencies 쿼리 파라미터
# ===========================================
class PriorityAgenciesParams(BaseModel):
    """우선 기관 엑셀 내보내기 쿼리 파라미터"""

    agencies: str = Field(..., min_length=1, max_length=1000, description="콤마로 구분된 기관명")

    @field_validator("agencies")
    @classmethod
    def validate_agencies(cls, v: str) -> str:
        """기관명 목록 검증"""
        agencies_list = [a.strip() for a in v.split(",")]
        if len(agencies_list) > 20:
            raise ValueError("최대 20개 기관까지 지정 가능합니다.")
        for agency in agencies_list:
            if len(agency) < 1 or len(agency) > 100:
                raise ValueError(f"기관명은 1-100자 사이여야 합니다: {agency}")
        return v


# ===========================================
# GET /analytics/trends 쿼리 파라미터
# ===========================================
class TrendsQueryParams(BaseModel):
    """트렌드 조회 쿼리 파라미터"""

    days: int = Field(default=30, ge=1, le=365, description="조회 기간 (1-365일)")


# ===========================================
# POST /filters/exclude-keywords 요청 바디
# ===========================================
class KeywordParam(BaseModel):
    """제외 키워드 요청 파라미터"""

    keyword: str = Field(..., min_length=1, max_length=50, description="제외 키워드")

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        """키워드 유효성 검사"""
        if not v.strip():
            raise ValueError("키워드는 공백일 수 없습니다.")
        return v.strip()


# ===========================================
# 파일 업로드 검증
# ===========================================
class FileUploadParams(BaseModel):
    """파일 업로드 쿼리 파라미터"""

    title: str = Field(..., min_length=1, max_length=200, description="공고 제목")
    agency: str = Field(default="Unknown", max_length=200, description="기관명")
    url: str = Field(default="http://uploaded.file", max_length=500, description="원본 URL")


# ===========================================
# 공고 ID Path 검증
# ===========================================
class AnnouncementIdPath(BaseModel):
    """공고 ID 경로 파라미터"""

    announcement_id: int = Field(..., ge=1, description="공고 ID (양수)")


# ===========================================
# Celery Task ID Path 검증
# ===========================================
class TaskIdPath(BaseModel):
    """Celery Task ID 경로 파라미터"""

    task_id: str = Field(..., min_length=1, max_length=100, description="Celery Task ID")

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Task ID 형식 검증"""
        import re

        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Task ID는 영문자, 숫자, 하이픈만 포함할 수 있습니다.")
        return v
