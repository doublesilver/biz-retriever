from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.core import security
from app.db.models import User
from pydantic import BaseModel, EmailStr

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # 1. Authenticate
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 2. Create Token
    access_token = security.create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserResponse)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Create new user.
    """
    # 1. Check existing
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
         raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # 2. Create User
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user
