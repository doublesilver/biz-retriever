from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models import User, UserKeyword
from app.schemas.keyword import UserKeywordCreate, UserKeywordResponse
from app.services.rate_limiter import limiter

router = APIRouter()


@router.post("/", response_model=UserKeywordResponse)
@limiter.limit("20/minute")
async def create_keyword(
    request: Request,
    keyword_in: UserKeywordCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    내 키워드 추가
    """
    # 중복 체크
    stmt = select(UserKeyword).where(
        UserKeyword.user_id == current_user.id,
        UserKeyword.keyword == keyword_in.keyword,
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Already exists")

    new_keyword = UserKeyword(
        user_id=current_user.id,
        keyword=keyword_in.keyword,
        category=keyword_in.category,
        is_active=keyword_in.is_active,
    )
    db.add(new_keyword)
    await db.commit()
    await db.refresh(new_keyword)
    return new_keyword


@router.get("/", response_model=List[UserKeywordResponse])
@limiter.limit("30/minute")
async def read_keywords(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    내 키워드 목록 조회
    """
    stmt = select(UserKeyword).where(UserKeyword.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{keyword_id}")
@limiter.limit("20/minute")
async def delete_keyword(
    request: Request,
    keyword_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    키워드 삭제
    """
    stmt = select(UserKeyword).where(
        UserKeyword.id == keyword_id, UserKeyword.user_id == current_user.id
    )
    result = await db.execute(stmt)
    keyword = result.scalars().first()

    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await db.delete(keyword)
    await db.commit()
    return {"message": "Deleted"}
