"""
표준 API 응답 스키마 (Enterprise Pattern)

모든 API 응답을 통일된 envelope 포맷으로 감싸는 제네릭 래퍼.

성공 응답:
    {
        "success": true,
        "data": { ... },
        "meta": { "page": 1, "total": 100 }
    }

에러 응답:
    {
        "success": false,
        "error": {
            "code": "AUTH_INVALID_CREDENTIALS",
            "message": "인증에 실패했습니다.",
            "details": { ... }
        }
    }
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ============================================
# Error Schema
# ============================================


class ErrorDetail(BaseModel):
    """구조화된 에러 정보"""

    code: str = Field(..., description="도메인별 에러 코드 (예: AUTH_001)")
    message: str = Field(..., description="사용자용 에러 메시지")
    details: Any | None = Field(default=None, description="추가 에러 상세 (개발 환경 전용)")
    path: str | None = Field(default=None, description="요청 경로")


# ============================================
# Pagination Meta
# ============================================


class PaginationMeta(BaseModel):
    """페이지네이션 메타 정보"""

    page: int = Field(..., ge=1, description="현재 페이지 번호")
    per_page: int = Field(..., ge=1, description="페이지당 항목 수")
    total: int = Field(..., ge=0, description="전체 항목 수")
    total_pages: int = Field(..., ge=0, description="전체 페이지 수")


# ============================================
# API Response Wrapper
# ============================================


class ApiResponse(BaseModel, Generic[T]):
    """
    표준 API 응답 Envelope.

    성공 시: success=True, data=..., error=None
    실패 시: success=False, data=None, error=ErrorDetail(...)
    """

    success: bool = Field(..., description="요청 성공 여부")
    data: T | None = Field(default=None, description="응답 데이터")
    error: ErrorDetail | None = Field(default=None, description="에러 정보 (실패 시)")
    meta: dict[str, Any] | None = Field(default=None, description="메타 정보 (페이지네이션 등)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="응답 시각 (UTC)")


# ============================================
# Helper Functions
# ============================================


def ok(data: Any = None, *, meta: dict[str, Any] | None = None) -> dict:
    """
    성공 응답을 생성하는 헬퍼.

    Usage:
        return ok({"id": 1, "name": "test"})
        return ok(items, meta={"page": 1, "total": 100})
    """
    response = {
        "success": True,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if meta is not None:
        response["meta"] = meta
    return response


def ok_paginated(
    items: list,
    *,
    total: int,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    페이지네이션 성공 응답 헬퍼.

    Usage:
        return ok_paginated(bids, total=250, skip=0, limit=20)
    """
    page = (skip // limit) + 1 if limit > 0 else 1
    total_pages = (total + limit - 1) // limit if limit > 0 else 1

    return {
        "success": True,
        "data": items,
        "meta": {
            "page": page,
            "per_page": limit,
            "total": total,
            "total_pages": total_pages,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


def fail(
    *,
    code: str,
    message: str,
    details: Any = None,
    path: str | None = None,
) -> dict:
    """
    에러 응답을 생성하는 헬퍼.

    Usage:
        return fail(code="AUTH_001", message="Invalid token")
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "path": path,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================
# Backward Compatibility
# ============================================


class ErrorResponse(BaseModel):
    """
    Standard Error Response Schema (legacy)
    """

    code: str
    message: str
    details: Any | None = None
