import secrets
from typing import Any, List, Optional

from fastapi import (APIRouter, Body, Depends, HTTPException, Request,
                     Response, status)
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.core.exceptions import WeakPasswordError
from app.core.logging import logger
from app.db.models import User
from app.services.rate_limiter import limiter

router = APIRouter()


class Token(BaseModel):
    """JWT 토큰 쌍 (Access + Refresh)"""

    access_token: str = Field(
        ...,
        description="JWT Access Token (15분 유효)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
    refresh_token: str = Field(
        ...,
        description="JWT Refresh Token (30일 유효)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    )
    token_type: str = Field(default="bearer", description="토큰 타입", example="bearer")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """Refresh Token 요청"""

    refresh_token: str = Field(..., description="JWT Refresh Token")


class TokenRefreshResponse(BaseModel):
    """Token Refresh 응답"""

    access_token: str = Field(..., description="새로 발급된 JWT Access Token")
    refresh_token: str = Field(..., description="새로 발급된 JWT Refresh Token")
    token_type: str = Field(default="bearer", description="토큰 타입")


class UserCreate(BaseModel):
    """사용자 생성 요청"""

    email: EmailStr = Field(
        ..., description="사용자 이메일", example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="비밀번호 (최소 8자, 대/소문자/숫자/특수문자 포함)",
        example="SecurePass123!",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "newuser@example.com", "password": "SecurePass123!"}]
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
            "examples": [{"id": 1, "email": "user@example.com", "is_active": True}]
        },
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
                        "token_type": "bearer",
                    }
                }
            },
        },
        400: {
            "description": "인증 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_credentials": {
                            "summary": "잘못된 인증 정보",
                            "value": {"detail": "Incorrect email or password"},
                        },
                        "inactive_user": {
                            "summary": "비활성화된 사용자",
                            "value": {"detail": "Inactive user"},
                        },
                        "account_locked": {
                            "summary": "계정 잠금",
                            "value": {
                                "detail": "Account locked due to too many failed login attempts. Try again later."
                            },
                        },
                    }
                }
            },
        },
        429: {
            "description": "요청 제한 초과",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 5 per 1 minute"}
                }
            },
        },
    },
)
@limiter.limit("5/minute")
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    ## OAuth2 호환 로그인

    이메일과 비밀번호로 인증하여 JWT 액세스 토큰을 발급받습니다.

    ### 사용 방법
    1. `username` 필드에 이메일 입력
    2. `password` 필드에 비밀번호 입력
    3. 발급받은 토큰을 `Authorization: Bearer <token>` 헤더로 사용

    ### 토큰 유효기간
    - Access Token: 15분
    - Refresh Token: 30일

    ### 보안 강화
    - 로그인 5회 실패 시 계정 30분 잠금
    - 잠금 해제 후 자동으로 재시도 가능
    """
    from datetime import datetime, timedelta

    # 1. Get User
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user:
        # User not found - generic error to prevent email enumeration
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # 2. Check if account is locked
    if user.locked_until:
        if datetime.utcnow() < user.locked_until:
            remaining_time = (user.locked_until - datetime.utcnow()).seconds // 60
            raise HTTPException(
                status_code=400,
                detail=f"Account locked due to too many failed login attempts. Try again in {remaining_time} minutes.",
            )
        else:
            # Lock expired - reset
            user.locked_until = None
            user.failed_login_attempts = 0
            await db.commit()

    # 3. Verify password
    if not security.verify_password(form_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await db.commit()
            raise HTTPException(
                status_code=400,
                detail="Account locked due to too many failed login attempts. Try again in 30 minutes.",
            )

        await db.commit()
        remaining_attempts = 5 - user.failed_login_attempts
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect email or password. {remaining_attempts} attempts remaining before account lock.",
        )

    # 4. Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 5. Login successful - reset failed attempts
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # 6. Create Token Pair (Access + Refresh)
    tokens = security.create_token_pair(subject=user.email)

    logger.info(f"User logged in successfully: {user.email}")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
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
                        "is_active": True,
                    }
                }
            },
        },
        400: {
            "description": "검증 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "weak_password": {
                            "summary": "약한 비밀번호",
                            "value": {
                                "detail": "비밀번호는 최소 8자 이상이어야 합니다."
                            },
                        },
                        "duplicate_email": {
                            "summary": "중복된 이메일",
                            "value": {
                                "detail": "The user with this email already exists in the system."
                            },
                        },
                    }
                }
            },
        },
        429: {
            "description": "요청 제한 초과",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded: 3 per 1 minute"}
                }
            },
        },
    },
)
@limiter.limit("3/minute")
async def register(
    request: Request, user_in: UserCreate, db: AsyncSession = Depends(deps.get_db)
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
    logger.info(f"Registering user: {user_in.email}")
    try:
        security.validate_password(user_in.password)
        logger.info("Password validation passed")
    except WeakPasswordError as e:
        logger.info(f"Password validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Check existing
    logger.info("Checking for existing user...")
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        logger.info("User already exists")
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    # 3. Create User
    logger.info("Creating new user object...")
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
    )
    logger.info("Adding user to DB session...")
    db.add(user)
    logger.info("Committing to DB...")
    await db.commit()
    logger.info("Refreshing user object...")
    await db.refresh(user)

    logger.info("Registration successful")
    return user


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="사용자 목록 조회",
    description="시스템의 모든 활성 사용자를 조회합니다. (담당자 지정용)",
)
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    모든 활성 사용자 목록을 반환합니다.
    칸반 보드에서 담당자 지정 시 사용됩니다.
    """
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()
    return users


# --- OAuth2 Social Login Removed ---
# Kakao and Naver OAuth2 integrations have been removed for security and maintenance reasons.
# Only email/password authentication is now supported.


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="토큰 갱신",
    description="Refresh Token으로 새로운 Access Token과 Refresh Token을 발급받습니다.",
    responses={
        200: {
            "description": "토큰 갱신 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "유효하지 않은 Refresh Token",
            "content": {
                "application/json": {"example": {"detail": "Invalid refresh token"}}
            },
        },
    },
)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    ## Refresh Token으로 토큰 갱신

    Access Token이 만료되었을 때 Refresh Token으로 새로운 토큰 쌍을 발급받습니다.

    ### 보안 강화
    - Access Token 유효기간: 15분 (탈취 시 피해 최소화)
    - Refresh Token 유효기간: 30일
    - Refresh Token도 함께 갱신 (Rotation)

    ### 사용 방법
    1. 로그인 시 받은 `refresh_token` 제공
    2. 새로운 `access_token`과 `refresh_token` 수령
    3. 기존 Refresh Token 폐기
    """
    # Verify Refresh Token and get user
    user = await security.verify_refresh_token(refresh_request.refresh_token, db)

    # Blacklist old refresh token (rotation)
    await security.blacklist_token(refresh_request.refresh_token, "refresh")

    # Create new token pair
    tokens = security.create_token_pair(subject=user.email)

    logger.info(f"Token refreshed for user: {user.email}")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="로그아웃",
    description="현재 로그인된 세션을 종료하고 토큰을 무효화합니다.",
    responses={
        200: {
            "description": "로그아웃 성공",
            "content": {
                "application/json": {"example": {"message": "Successfully logged out"}}
            },
        },
        401: {
            "description": "인증 실패",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
    },
)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    token: str = Depends(security.oauth2_scheme),
) -> Any:
    """
    ## 로그아웃

    현재 사용중인 Access Token을 블랙리스트에 추가하여 무효화합니다.

    ### 동작 방식
    1. 현재 토큰을 Redis 블랙리스트에 추가
    2. 토큰 만료 시간까지 블랙리스트 유지
    3. 클라이언트에서 토큰 삭제 필요

    ### 보안 참고
    - Refresh Token도 함께 무효화하려면 클라이언트에서 삭제 필요
    - Access Token은 자동으로 블랙리스트 처리
    """
    # Blacklist the current access token
    await security.blacklist_token(token, "access")

    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Successfully logged out"}
