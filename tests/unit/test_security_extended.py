"""
Security 모듈 확장 단위 테스트
- JWT Access/Refresh Token 생성 및 검증
- Token Pair 생성
- Refresh Token 검증
- Token 블랙리스트
- Password 해싱/검증
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.core.exceptions import WeakPasswordError
from app.core.security import (
    ALGORITHM,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    get_password_hash,
    is_token_blacklisted,
    validate_password,
    verify_password,
    verify_refresh_token,
)


class TestCreateAccessToken:
    """Access Token 생성 테스트"""

    def test_creates_valid_jwt(self):
        token = create_access_token(subject="user@test.com")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@test.com"
        assert payload["type"] == "access"

    def test_default_expiry(self):
        token = create_access_token(subject="user@test.com")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        # 만료 시간이 현재부터 ACCESS_TOKEN_EXPIRE_MINUTES 이내
        assert exp > now
        assert (exp - now).total_seconds() <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 5

    def test_custom_expiry(self):
        delta = timedelta(hours=2)
        token = create_access_token(subject="user@test.com", expires_delta=delta)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        assert (exp - now).total_seconds() > 3600  # 1시간 이상

    def test_subject_converted_to_string(self):
        token = create_access_token(subject=42)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"


class TestCreateRefreshToken:
    """Refresh Token 생성 테스트"""

    def test_creates_refresh_type(self):
        token = create_refresh_token(subject="user@test.com")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"

    def test_30_day_expiry(self):
        token = create_refresh_token(subject="user@test.com")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        # 약 30일 후 만료
        diff_days = (exp - now).days
        assert 29 <= diff_days <= 31


class TestCreateTokenPair:
    """Token Pair 생성 테스트"""

    def test_returns_both_tokens(self):
        pair = create_token_pair(subject="user@test.com")
        assert "access_token" in pair
        assert "refresh_token" in pair

    def test_access_token_type(self):
        pair = create_token_pair(subject="user@test.com")
        payload = jwt.decode(pair["access_token"], settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "access"

    def test_refresh_token_type(self):
        pair = create_token_pair(subject="user@test.com")
        payload = jwt.decode(pair["refresh_token"], settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"


class TestPasswordValidation:
    """비밀번호 정책 검증 테스트"""

    def test_valid_password(self):
        validate_password("StrongPass123!")  # 예외 없으면 통과

    def test_too_short(self):
        with pytest.raises(WeakPasswordError):
            validate_password("Ab1!")

    def test_no_uppercase(self):
        with pytest.raises(WeakPasswordError):
            validate_password("lowercase123!")

    def test_no_lowercase(self):
        with pytest.raises(WeakPasswordError):
            validate_password("UPPERCASE123!")

    def test_no_digit(self):
        with pytest.raises(WeakPasswordError):
            validate_password("NoDigits!@#")

    def test_no_special_char(self):
        with pytest.raises(WeakPasswordError):
            validate_password("NoSpecial123")


class TestPasswordHashing:
    """비밀번호 해싱/검증 테스트"""

    def test_hash_and_verify(self):
        password = "TestPass123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = get_password_hash("CorrectPass123!")
        assert verify_password("WrongPass123!", hashed) is False

    def test_hash_is_different_each_time(self):
        h1 = get_password_hash("SamePass123!")
        h2 = get_password_hash("SamePass123!")
        assert h1 != h2  # bcrypt salt가 달라서

    def test_hash_is_bcrypt_format(self):
        hashed = get_password_hash("TestPass123!")
        assert hashed.startswith("$2b$")


class TestVerifyRefreshToken:
    """Refresh Token 검증 테스트"""

    async def test_valid_refresh_token(self):
        """유효한 Refresh Token"""
        token = create_refresh_token("test@example.com")
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        user = await verify_refresh_token(token, mock_session)
        assert user.email == "test@example.com"

    async def test_access_token_rejected(self):
        """Access Token을 Refresh로 사용하면 거부"""
        token = create_access_token("test@example.com")
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await verify_refresh_token(token, mock_session)
        assert exc_info.value.status_code == 401

    async def test_invalid_token_rejected(self):
        """유효하지 않은 토큰 거부"""
        mock_session = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await verify_refresh_token("invalid.token.here", mock_session)
        assert exc_info.value.status_code == 401

    async def test_user_not_found(self):
        """토큰은 유효하나 사용자 없음"""
        token = create_refresh_token("nonexistent@example.com")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await verify_refresh_token(token, mock_session)
        assert exc_info.value.status_code == 401


class TestTokenBlacklist:
    """토큰 블랙리스트 테스트"""

    @patch("app.core.cache.get_redis")
    async def test_blacklist_token(self, mock_get_redis):
        """토큰을 블랙리스트에 추가"""
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        token = create_access_token("test@example.com")
        await blacklist_token(token, "access")

        # Redis setex 호출 확인
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert "blacklist:access:" in args[0][0]

    @patch("app.core.cache.get_redis")
    async def test_is_token_blacklisted_false(self, mock_get_redis):
        """블랙리스트에 없는 토큰"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        result = await is_token_blacklisted("some_token", "access")
        assert result is False

    @patch("app.core.cache.get_redis")
    async def test_is_token_blacklisted_true(self, mock_get_redis):
        """블랙리스트에 있는 토큰"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "1"
        mock_get_redis.return_value = mock_redis

        result = await is_token_blacklisted("some_token", "access")
        assert result is True

    @patch("app.core.cache.get_redis")
    async def test_redis_failure_returns_true(self, mock_get_redis):
        """Redis 장애 시 안전하게 거부 (fail closed)"""
        mock_get_redis.side_effect = Exception("Redis connection failed")

        result = await is_token_blacklisted("some_token", "access")
        assert result is True  # 안전하게 거부

    @patch("app.core.cache.get_redis")
    async def test_blacklist_redis_failure_silent(self, mock_get_redis):
        """블랙리스트 추가 시 Redis 장애는 조용히 처리"""
        mock_get_redis.side_effect = Exception("Redis connection failed")

        token = create_access_token("test@example.com")
        # 예외가 발생하지 않아야 함
        await blacklist_token(token, "access")
