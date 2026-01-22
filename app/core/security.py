from datetime import datetime, timedelta
from typing import Any, Union
import re
from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import WeakPasswordError
from app.core.logging import logger
from app.db.session import get_db
from app.db.models import User

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
    
    if not re.search(r'[A-Z]', password):
        raise WeakPasswordError("비밀번호에 대문자가 포함되어야 합니다.")
    
    if not re.search(r'[a-z]', password):
        raise WeakPasswordError("비밀번호에 소문자가 포함되어야 합니다.")
    
    if not re.search(r'[0-9]', password):
        raise WeakPasswordError("비밀번호에 숫자가 포함되어야 합니다.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise WeakPasswordError("비밀번호에 특수문자가 포함되어야 합니다.")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """JWT 액세스 토큰 생성"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db)
) -> User:
    """
    현재 인증된 사용자 조회
    
    Args:
        token: JWT 토큰
        session: DB 세션
    
    Returns:
        User 객체
    
    Raises:
        HTTPException: 인증 실패 시
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        logger.warning("Invalid JWT token")
        raise credentials_exception
    
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"User not found: {email}")
        raise credentials_exception
    
    return user
