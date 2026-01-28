import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from fastapi_cache.decorator import cache

from app.api import deps
from app.schemas.bid import BidCreate, BidResponse, BidUpdate, BidListResponse
from app.schemas.query import BidsQueryParams, FileUploadParams
from app.services.bid_service import bid_service
from app.services.file_service import file_service
from app.worker.tasks import process_bid_analysis
from app.db.models import BidAnnouncement, User
from app.core.logging import logger
from app.utils.db_utils import get_object_or_404
from app.core.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE_BYTES

router = APIRouter()
logger.info("CORE_MODULE_LOADED: bids.py with BidListResponse")

# File upload constraints (moved to constants.py)
ALLOWED_EXTENSIONS = ALLOWED_FILE_EXTENSIONS
MAX_FILE_SIZE = MAX_FILE_SIZE_BYTES


@router.post(
    "/",
    response_model=BidResponse,
    status_code=status.HTTP_201_CREATED,
    summary="입찰 공고 생성",
    responses={
        201: {"description": "공고 생성 성공"},
        401: {"description": "인증 필요"},
        422: {"description": "입력값 검증 실패"},
    }
)
async def create_bid(
    bid_in: BidCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    새로운 입찰 공고를 생성합니다.

    - **title**: 공고 제목 (필수)
    - **content**: 공고 내용 (필수)
    - **agency**: 발주 기관명
    - **posted_at**: 게시일시
    - **url**: 원본 공고 URL
    """
    return await bid_service.create_bid(db, bid_in)


@router.get(
    "/{bid_id}",
    response_model=BidResponse,
    summary="입찰 공고 상세 조회",
    responses={
        200: {"description": "조회 성공"},
        404: {"description": "공고를 찾을 수 없음"},
    }
)
async def read_bid(
    bid_id: int = Path(..., ge=1, description="공고 ID (양수)", example=1),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    특정 입찰 공고의 상세 정보를 조회합니다.

    - **bid_id**: 조회할 공고의 고유 ID
    """
    # Use utility function instead of duplicate code
    return await get_object_or_404(db, BidAnnouncement, bid_id, "Bid not found")


@router.patch(
    "/{bid_id}",
    response_model=BidResponse,
    summary="입찰 공고 수정 (상태/담당자 변경)",
    responses={
        200: {"description": "수정 성공"},
        404: {"description": "공고를 찾을 수 없음"},
    }
)
async def update_bid(
    bid_in: BidUpdate,
    bid_id: int = Path(..., ge=1, description="공고 ID"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    입찰 공고의 상태 또는 담당자를 변경합니다.
    """
    bid = await bid_service.get_bid(db, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    
    # Update
    updated_bid = await bid_service.update_bid(db, bid, bid_in)
    return updated_bid


@router.get("/", response_model=BidListResponse)
@cache(expire=60)
async def read_bids(
    skip: int = Query(default=0, ge=0, description="건너뛸 개수"),
    limit: int = Query(default=100, ge=1, le=500, description="조회 개수 (최대 500)"),
    keyword: Optional[str] = Query(default=None, min_length=1, max_length=100, description="검색 키워드"),
    agency: Optional[str] = Query(default=None, min_length=1, max_length=200, description="기관명"),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Retrieve bids with optional filtering and caching (60s).

    - **skip**: 건너뛸 개수 (기본 0)
    - **limit**: 조회 개수 (최대 500)
    - **keyword**: 제목/내용 검색 키워드
    - **agency**: 기관명 필터
    """
    # SQL Injection 방지를 위한 특수문자 제거
    if keyword:
        keyword = keyword.replace("'", "").replace('"', "").replace(";", "").strip()

    bids = await bid_service.get_bids(
        db,
        skip=skip,
        limit=limit,
        keyword=keyword,
        agency=agency
    )
    
    # [FIX] Get total count for pagination
    from sqlalchemy import func
    total_result = await db.execute(select(func.count(BidAnnouncement.id)))
    total = total_result.scalar()

    return {
        "items": bids,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/upload", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def upload_bid(
    file: UploadFile = File(..., description="PDF 또는 HWP 파일"),
    title: str = Query(..., min_length=1, max_length=200, description="공고 제목"),
    agency: str = Query(default="Unknown", max_length=200, description="기관명"),
    url: str = Query(default="http://uploaded.file", max_length=500, description="원본 URL"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Upload a PDF/HWP file, extract text, and create a bid.
    Triggers async analysis.

    - 지원 파일 형식: PDF, HWP
    - 최대 파일 크기: 10MB
    """
    # 파일 확장자 검증
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 필요합니다.")

    filename = file.filename.lower()
    ext = os.path.splitext(filename)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 파일 크기 검증
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # 파일 포인터 리셋
    await file.seek(0)

    logger.info(f"파일 업로드: {filename}, size={len(content)}, user={current_user.email}")

    # 1. Extract Text
    text_content = await file_service.get_text_from_file(file)

    # 2. Create Bid Object
    bid_in = BidCreate(
        title=title,
        content=text_content,
        agency=agency,
        posted_at=datetime.now(),
        url=f"{url}/{file.filename}-{datetime.now().timestamp()}"  # Fake unique URL
    )

    # 3. Save to DB
    new_bid = await bid_service.create_bid(db, bid_in)

    # 4. Trigger Analysis Worker
    process_bid_analysis.delay(new_bid.id)

    logger.info(f"공고 생성 완료: id={new_bid.id}, title={title}")

    return new_bid
