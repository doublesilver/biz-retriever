"""
security.get_current_user 분기 커버리지 테스트
- 블랙리스트된 토큰
- 유효하지 않은 JWT
- email=None
- 사용자 미발견
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    get_current_user,
    get_current_user_from_token,
)


class TestGetCurrentUserBranches:
    """get_current_user 미커버 분기"""

    async def test_blacklisted_token_raises(self):
        """블랙리스트된 토큰 -> 401"""
        token = create_access_token("test@example.com")
        mock_session = AsyncMock()

        with patch("app.core.security.is_token_blacklisted", AsyncMock(return_value=True)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, session=mock_session)
            assert exc_info.value.status_code == 401

    async def test_invalid_jwt_raises(self):
        """유효하지 않은 JWT -> 401"""
        mock_session = AsyncMock()

        with patch("app.core.security.is_token_blacklisted", AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="not.a.valid.jwt", session=mock_session)
            assert exc_info.value.status_code == 401

    async def test_no_email_in_payload_raises(self):
        """JWT에 sub 없음 -> 401"""
        from jose import jwt as jose_jwt

        # sub 없는 토큰 생성
        token = jose_jwt.encode(
            {"type": "access", "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        mock_session = AsyncMock()

        with patch("app.core.security.is_token_blacklisted", AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, session=mock_session)
            assert exc_info.value.status_code == 401

    async def test_user_not_found_raises(self):
        """유효한 토큰이지만 DB에 사용자 없음 -> 401"""
        token = create_access_token("ghost@example.com")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with patch("app.core.security.is_token_blacklisted", AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token=token, session=mock_session)
            assert exc_info.value.status_code == 401


class TestGetCurrentUserFromTokenBranches:
    """get_current_user_from_token 미커버 분기"""

    async def test_no_email_returns_none(self):
        """JWT에 sub 없음 -> None"""
        from jose import jwt as jose_jwt

        token = jose_jwt.encode(
            {"type": "access", "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )

        result = await get_current_user_from_token(token)
        assert result is None

    async def test_invalid_jwt_returns_none(self):
        """유효하지 않은 JWT -> None"""
        result = await get_current_user_from_token("bad.token.here")
        assert result is None
