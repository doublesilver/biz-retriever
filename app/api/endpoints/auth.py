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
    """JWT 액세스 토큰"""

    access_token: str = Field(..., description="JWT 액세스 토큰", example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", description="토큰 타입", example="bearer")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDk4MDk1NDEsInN1YiI6InRlc3RAZXhhbXBsZS5jb20ifQ...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class UserCreate(BaseModel):
    """사용자 생성 요청"""

    email: EmailStr = Field(..., description="사용자 이메일", example="user@example.com")
    password: str = Field(
        ..., min_length=8, description="비밀번호 (최소 8자, 대/소문자/숫자/특수문자 포함)", example="SecurePass123!"
    )

    model_config = {"json_schema_extra": {"examples": [{"email": "newuser@example.com", "password": "SecurePass123!"}]}}


class UserResponse(BaseModel):
    """사용자 응답"""

    id: int = Field(..., description="사용자 ID", example=1)
    email: str = Field(..., description="사용자 이메일", example="user@example.com")
    is_active: bool = Field(default=True, description="활성화 상태", example=True)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {"examples": [{"id": 1, "email": "user@example.com", "is_active": True}]},
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
                    "example": {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
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
                        "inactive_user": {"summary": "비활성화된 사용자", "value": {"detail": "Inactive user"}},
                    }
                }
            },
        },
        429: {
            "description": "요청 제한 초과",
            "content": {"application/json": {"example": {"detail": "Rate limit exceeded: 5 per 1 minute"}}},
        },
    },
)
@limiter.limit("5/minute")
async def login_access_token(
    request: Request, db: AsyncSession = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
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
            "content": {"application/json": {"example": {"id": 1, "email": "newuser@example.com", "is_active": True}}},
        },
        400: {
            "description": "검증 실패",
            "content": {
                "application/json": {
                    "examples": {
                        "weak_password": {
                            "summary": "약한 비밀번호",
                            "value": {"detail": "비밀번호는 최소 8자 이상이어야 합니다."},
                        },
                        "duplicate_email": {
                            "summary": "중복된 이메일",
                            "value": {"detail": "The user with this email already exists in the system."},
                        },
                    }
                }
            },
        },
        429: {
            "description": "요청 제한 초과",
            "content": {"application/json": {"example": {"detail": "Rate limit exceeded: 3 per 1 minute"}}},
        },
    },
)
@limiter.limit("3/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(deps.get_db)) -> Any:
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
    user = User(email=user_in.email, hashed_password=security.get_password_hash(user_in.password), is_active=True)
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
    db: AsyncSession = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    모든 활성 사용자 목록을 반환합니다.
    칸반 보드에서 담당자 지정 시 사용됩니다.
    """
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()
    return users


# --- SNS Login ---


@router.get("/login/{provider}")
async def login_sns(provider: str):
    """
    SNS 로그인 리다이렉트 (Google, Kakao, Naver)
    """
    import urllib.parse

    from app.core.config import settings

    if provider == "kakao":
        client_id = settings.KAKAO_CLIENT_ID
        redirect_uri = settings.KAKAO_REDIRECT_URI
        auth_url = "https://kauth.kakao.com/oauth/authorize"
        url = f"{auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
        return RedirectResponse(url=url)

    elif provider == "naver":
        client_id = settings.NAVER_CLIENT_ID
        redirect_uri = settings.NAVER_REDIRECT_URI
        auth_url = "https://nid.naver.com/oauth2.0/authorize"
        state = secrets.token_urlsafe(32)  # CSRF protection with cryptographically secure random state
        url = f"{auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}"
        return RedirectResponse(url=url)

    raise HTTPException(status_code=400, detail="Unsupported provider")


@router.get("/callback/{provider}")
async def callback_sns(provider: str, code: str, state: Optional[str] = None, db: AsyncSession = Depends(deps.get_db)):
    """
    SNS 로그인 콜백 처리
    1. 토큰 발급
    2. 사용자 정보 조회
    3. 회원가입/로그인 처리
    4. JWT 토큰 발급
    """
    import httpx

    from app.core.config import settings

    user_email = ""
    social_id = ""
    profile_image = ""

    try:
        async with httpx.AsyncClient() as client:
            if provider == "kakao":
                # Get Token
                token_url = "https://kauth.kakao.com/oauth/token"
                data = {
                    "grant_type": "authorization_code",
                    "client_id": settings.KAKAO_CLIENT_ID,
                    "redirect_uri": settings.KAKAO_REDIRECT_URI,
                    "code": code,
                    "client_secret": settings.KAKAO_CLIENT_SECRET,
                }
                # Header content-type for Kakao
                headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
                res = await client.post(token_url, data=data, headers=headers)
                res.raise_for_status()
                token_data = res.json()

                # Get User Info
                user_info_res = await client.get(
                    "https://kapi.kakao.com/v2/user/me",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                )
                user_info = user_info_res.json()

                social_id = str(user_info.get("id"))
                kakao_account = user_info.get("kakao_account", {})
                user_email = kakao_account.get("email")
                profile = kakao_account.get("profile", {})
                # profile_image = profile.get("thumbnail_image_url") # Optional

            elif provider == "naver":
                # Get Token
                token_url = "https://nid.naver.com/oauth2.0/token"
                params = {
                    "grant_type": "authorization_code",
                    "client_id": settings.NAVER_CLIENT_ID,
                    "client_secret": settings.NAVER_CLIENT_SECRET,
                    "code": code,
                    "state": state,
                }
                res = await client.get(token_url, params=params)
                res.raise_for_status()
                token_data = res.json()

                # Get User Info
                user_info_res = await client.get(
                    "https://openapi.naver.com/v1/nid/me",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                )
                user_info = user_info_res.json().get("response", {})

                social_id = user_info.get("id")
                user_email = user_info.get("email")
                profile_image = user_info.get("profile_image")

    except Exception as e:
        logger.error(f"SNS Auth Error ({provider}): {e}")
        raise HTTPException(status_code=400, detail="SNS Authentication Failed")

    if not user_email:
        raise HTTPException(status_code=400, detail="Email not provided by SNS")

    # DB Logic
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()

    if not user:
        # Create New User (Auto Register)
        import secrets

        random_password = secrets.token_urlsafe(16)

        user = User(
            email=user_email,
            hashed_password=security.get_password_hash(random_password),
            is_active=True,
            provider=provider,
            provider_id=social_id,
            profile_image=profile_image,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    else:
        # Update existing user info if needed
        if not user.provider:
            user.provider = provider
            user.provider_id = social_id

        if profile_image and not user.profile_image:
            user.profile_image = profile_image

        await db.commit()

    # Create JWT
    access_token = security.create_access_token(subject=user.email)

    # Redirect to Frontend with token in HttpOnly cookie (NOT in URL)
    redirect_url = f"{settings.FRONTEND_URL}/dashboard.html?login=success"
    response = RedirectResponse(url=redirect_url, status_code=302)

    # Set HttpOnly cookie for security (prevents XSS token theft)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # Only send over HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 8,  # 8 days
        path="/",
    )
    return response
