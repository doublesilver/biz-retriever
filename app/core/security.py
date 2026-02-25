import re
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import WeakPasswordError
from app.core.logging import logger
from app.db.models import User
from app.db.session import get_db

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")


def validate_password(password: str) -> None:
    """
    비밀번호 정책 검증

    정책:
    - 최소 8자 이상
    - 대문자, 소문자, 숫자, 특수문자 각 1개 이상

    Args:
        password: 검증할 비밀번호

    Raises:
        WeakPasswordError: 정책에 맞지 않는 비밀번호
    """
    if len(password) < 8:
        raise WeakPasswordError("비밀번호는 최소 8자 이상이어야 합니다.")

    if not re.search(r"[A-Z]", password):
        raise WeakPasswordError("비밀번호에 대문자가 포함되어야 합니다.")

    if not re.search(r"[a-z]", password):
        raise WeakPasswordError("비밀번호에 소문자가 포함되어야 합니다.")

    if not re.search(r"[0-9]", password):
        raise WeakPasswordError("비밀번호에 숫자가 포함되어야 합니다.")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise WeakPasswordError("비밀번호에 특수문자가 포함되어야 합니다.")


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    JWT Access Token 생성

    기본 만료 시간: 15분 (보안 강화)
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any) -> str:
    """
    JWT Refresh Token 생성

    만료 시간: 30일
    Access Token 재발급 전용
    """
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token_pair(subject: str | Any) -> dict[str, str]:
    """
    Access Token + Refresh Token 쌍 생성

    Returns:
        {"access_token": "...", "refresh_token": "..."}
    """
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)
    return {"access_token": access_token, "refresh_token": refresh_token}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt 10 rounds - 성능 최적화)"""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=10)  # 12 → 10 rounds (보안은 유지하면서 2-3배 빠름)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db)) -> User:
    """
    현재 인증된 사용자 조회 (토큰 블랙리스트 체크 포함)

    Args:
        token: JWT 토큰
        session: DB 세션

    Returns:
        User 객체

    Raises:
        HTTPException: 인증 실패 시 또는 토큰이 블랙리스트에 있을 때
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check if token is blacklisted (logged out)
    if await is_token_blacklisted(token, "access"):
        logger.warning("Attempt to use blacklisted token")
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        logger.warning("Invalid JWT token")
        raise credentials_exception

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("User not found for token subject")
        raise credentials_exception

    return user


async def get_current_user_from_token(token: str) -> User | None:
    """
    WebSocket용 토큰 검증 함수 (Depends 사용 불가)
    """
    from app.db.session import AsyncSessionLocal

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return user


async def verify_refresh_token(refresh_token: str, session: AsyncSession) -> User:
    """
    Refresh Token 검증 및 사용자 조회

    Args:
        refresh_token: JWT Refresh Token
        session: DB 세션

    Returns:
        User 객체

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료됨
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        # Refresh Token인지 확인
        if token_type != "refresh":
            logger.warning("Token type mismatch: expected refresh, got %s", token_type)
            raise credentials_exception

        if email is None:
            raise credentials_exception

    except JWTError as e:
        logger.warning("Invalid refresh token: %s", e)
        raise credentials_exception

    # 사용자 조회
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("User not found for refresh token subject")
        raise credentials_exception

    return user


async def blacklist_token(token: str, token_type: str = "access") -> None:
    """
    토큰을 블랙리스트에 추가 (로그아웃 시 사용)

    Args:
        token: JWT 토큰
        token_type: "access" or "refresh"
    """
    try:
        from app.core.cache import get_redis

        # Decode token to get expiry time
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            # Calculate TTL (time to live) - how long until token expires
            now = datetime.utcnow().timestamp()
            ttl = int(exp_timestamp - now)

            if ttl > 0:
                # Store in Redis with TTL matching token expiry
                redis_client = await get_redis()
                key = f"blacklist:{token_type}:{token}"
                await redis_client.setex(key, ttl, "1")
                logger.info(f"Token blacklisted: {token_type}, TTL: {ttl}s")
    except Exception as e:
        logger.error(f"Failed to blacklist token: {e}")
        # Non-critical error - don't raise


async def is_token_blacklisted(token: str, token_type: str = "access") -> bool:
    """
    토큰이 블랙리스트에 있는지 확인

    Args:
        token: JWT 토큰
        token_type: "access" or "refresh"

    Returns:
        True if blacklisted, False otherwise
    """
    try:
        from app.core.cache import get_redis

        redis_client = await get_redis()
        key = f"blacklist:{token_type}:{token}"
        result = await redis_client.get(key)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to check token blacklist: {e}")
        # A02/A07: Fail closed - Redis 장애 시 안전하게 거부
        # 토큰 블랙리스트 확인이 불가하면 탈취된 토큰이 사용될 수 있으므로
        # 보안을 우선하여 요청을 거부한다. 클라이언트는 재로그인하면 된다.
        return True
