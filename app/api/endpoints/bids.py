from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.schemas.bid import BidCreate, BidResponse, BidUpdate
from app.services.bid_service import bid_service
from app.db.models import BidAnnouncement, User

router = APIRouter()

@router.post("/", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid(
    bid_in: BidCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Create a new bid announcement.
    """
    return await bid_service.create_bid(db, bid_in)

@router.get("/{bid_id}", response_model=BidResponse)
async def read_bid(
    bid_id: int,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Get a specific bid by ID.
    """
    bid = await bid_service.get_bid(db, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid

from typing import Optional
from fastapi_cache.decorator import cache

@router.get("/", response_model=List[BidResponse])
@cache(expire=60)
async def read_bids(
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    agency: Optional[str] = None,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Retrieve bids with optional filtering and caching (60s).
    """
    return await bid_service.get_bids(
        db, 
        skip=skip, 
        limit=limit,
        keyword=keyword,
        agency=agency
    )

from fastapi import UploadFile, File
from app.services.file_service import file_service
from app.worker.tasks import process_bid_analysis
from datetime import datetime

@router.post("/upload", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def upload_bid(
    file: UploadFile = File(...),
    title: str = "Uploaded Bid",
    agency: str = "Unknown",
    url: str = "http://uploaded.file",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Upload a PDF/HWP file, extract text, and create a bid.
    Triggers async analysis.
    """
    # 1. Extract Text
    content = await file_service.get_text_from_file(file)
    
    # 2. Create Bid Object
    bid_in = BidCreate(
        title=title,
        content=content,
        agency=agency,
        posted_at=datetime.now(),
        url=f"{url}/{file.filename}-{datetime.now().timestamp()}" # Fake unique URL
    )
    
    # 3. Save to DB
    new_bid = await bid_service.create_bid(db, bid_in)
    
    # 4. Trigger Analysis Worker
    process_bid_analysis.delay(new_bid.id)
    
    return new_bid
