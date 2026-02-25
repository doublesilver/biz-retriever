"""
Security WebSocket 토큰 검증 단위 테스트
- get_current_user_from_token
"""

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.security import (
    create_access_token,
    get_current_user_from_token,
)


class TestGetCurrentUserFromToken:
    """WebSocket용 토큰 검증 테스트"""

    async def test_valid_token_returns_user(self):
        """유효한 토큰 → 사용자 반환"""
        token = create_access_token("ws_user@test.com")

        mock_user = MagicMock()
        mock_user.email = "ws_user@test.com"
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_local = MagicMock(return_value=mock_session)

        with patch("app.db.session.AsyncSessionLocal", mock_session_local):
            user = await get_current_user_from_token(token)
        assert user is not None
        assert user.email == "ws_user@test.com"

    async def test_invalid_token_returns_none(self):
        """유효하지 않은 토큰 → None"""
        result = await get_current_user_from_token("invalid.jwt.token")
        assert result is None

    async def test_empty_sub_returns_none(self):
        """sub 필드 없는 토큰 → None"""
        from datetime import datetime, timedelta

        from jose import jwt

        from app.core.config import settings
        from app.core.security import ALGORITHM

        token = jwt.encode(
            {"exp": datetime.utcnow() + timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        result = await get_current_user_from_token(token)
        assert result is None

    async def test_user_not_found_returns_none(self):
        """DB에 사용자 없으면 None"""
        token = create_access_token("nonexistent@test.com")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_local = MagicMock(return_value=mock_session)

        with patch("app.db.session.AsyncSessionLocal", mock_session_local):
            user = await get_current_user_from_token(token)
        assert user is None
