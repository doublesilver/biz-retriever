from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.core import security
from app.core.exceptions import WeakPasswordError
from app.db.models import User
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

class Token(BaseModel):
    """JWT 액세스 토큰"""
    access_token: str = Field(..., description="JWT 액세스 토큰", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", description="토큰 타입", example="bearer")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDk4MDk1NDEsInN1YiI6InRlc3RAZXhhbXBsZS5jb20ifQ...",
                "token_type": "bearer"
            }]
        }
    }

class UserCreate(BaseModel):
    """사용자 생성 요청"""
    email: EmailStr = Field(..., description="사용자 이메일", example="user@example.com")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자, 대/소문자/숫자/특수문자 포함)", example="SecurePass123!")
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }]
        }
    }

class UserResponse(BaseModel):
    """사용자 응답"""
    id: int = Field(..., description="사용자 ID", example=1)
    email: str = Field(..., description="사용자 이메일", example="user@example.com")
    is_active: bool = Field(default=True, description="활성화 상태", example=True)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": 1,
                "email": "user@example.com",
                "is_active": True
            }]
        }
    }

@router.post(
    "/login/access-token",
    response_model=Token,
    summary="로그인",
    description="이메일/비밀번호로 로그인하여 JWT 액세스 토큰을 발급받습니다.",
    responses={
        200: {
            "description": "로그인 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        400: {
            "description": "인증 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_credentials": {
                            "summary": "잘못된 인증 정보",
                            "value": {"detail": "Incorrect email or password"}
                        },
                        "inactive_user": {
                            "summary": "비활성화된 사용자",
                            "value": {"detail": "Inactive user"}
                        }
                    }
                }
            }
        }
    }
)
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    ## OAuth2 호환 로그인
    
    이메일과 비밀번호로 인증하여 JWT 액세스 토큰을 발급받습니다.
    
    ### 사용 방법
    1. `username` 필드에 이메일 입력
    2. `password` 필드에 비밀번호 입력
    3. 발급받은 토큰을 `Authorization: Bearer <token>` 헤더로 사용
    
    ### 토큰 유효기간
    - 기본: 8일
    - 만료 시 재로그인 필요
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

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="새로운 사용자 계정을 생성합니다.",
    responses={
        201: {
            "description": "회원가입 성공",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "newuser@example.com",
                        "is_active": True
                    }
                }
            }
        },
        400: {
            "description": "검증 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "weak_password": {
                            "summary": "약한 비밀번호",
                            "value": {"detail": "비밀번호는 최소 8자 이상이어야 합니다."}
                        },
                        "duplicate_email": {
                            "summary": "중복된 이메일",
                            "value": {"detail": "The user with this email already exists in the system."}
                        }
                    }
                }
            }
        }
    }
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    ## 회원가입
    
    새로운 사용자 계정을 생성합니다.
    
    ### 비밀번호 요구사항
    - 최소 8자 이상
    - 대문자 1개 이상
    - 소문자 1개 이상
    - 숫자 1개 이상
    - 특수문자 1개 이상 (!@#$%^&*(),.?\":{}|<>)
    
    ### 반환값
    생성된 사용자 정보 (비밀번호 제외)
    """
    # 1. Validate password strength
    try:
        security.validate_password(user_in.password)
    except WeakPasswordError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # 2. Check existing
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
         raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    # 3. Create User
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
