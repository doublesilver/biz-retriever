"""
비밀번호 재설정 기능 테스트
- password-reset-request: 재설정 이메일 발송
- password-reset-confirm: 토큰 검증 및 비밀번호 변경
"""

import secrets
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.db.models import User


class TestPasswordResetRequest:
    """비밀번호 재설정 요청 (POST /auth/password-reset-request)"""

    @pytest.mark.asyncio
    async def test_password_reset_request_existing_user(
        self, async_client: AsyncClient, test_user: User
    ):
        """존재하는 사용자에 대한 재설정 요청 - 성공 응답"""
        with patch("app.api.endpoints.auth.email_service") as mock_email:
            mock_email.is_configured.return_value = False
            response = await async_client.post(
                "/api/v1/auth/password-reset-request",
                json={"email": test_user.email},
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_password_reset_request_nonexistent_user(
        self, async_client: AsyncClient
    ):
        """존재하지 않는 사용자 - 동일한 성공 응답 (Enumeration 방지)"""
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_password_reset_request_invalid_email(
        self, async_client: AsyncClient
    ):
        """잘못된 이메일 형식 - 422 Validation Error"""
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_password_reset_generates_token(
        self, async_client: AsyncClient, test_user: User, test_db: AsyncSession
    ):
        """재설정 요청 시 토큰이 DB에 저장되는지 확인"""
        with patch("app.api.endpoints.auth.email_service") as mock_email:
            mock_email.is_configured.return_value = False
            await async_client.post(
                "/api/v1/auth/password-reset-request",
                json={"email": test_user.email},
            )

        await test_db.refresh(test_user)
        assert test_user.password_reset_token is not None
        assert test_user.password_reset_expires is not None
        assert test_user.password_reset_expires > datetime.utcnow()


class TestPasswordResetConfirm:
    """비밀번호 재설정 확인 (POST /auth/password-reset-confirm)"""

    @pytest.mark.asyncio
    async def test_password_reset_confirm_valid_token(
        self, async_client: AsyncClient, test_user: User, test_db: AsyncSession
    ):
        """유효한 토큰으로 비밀번호 재설정 - 성공"""
        # Setup: 직접 토큰 설정
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await test_db.commit()

        new_password = "NewStrongPass123!"
        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": reset_token, "new_password": new_password},
        )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

        # 비밀번호가 실제로 변경되었는지 확인
        await test_db.refresh(test_user)
        assert verify_password(new_password, test_user.hashed_password)
        assert test_user.password_reset_token is None
        assert test_user.password_reset_expires is None

    @pytest.mark.asyncio
    async def test_password_reset_confirm_expired_token(
        self, async_client: AsyncClient, test_user: User, test_db: AsyncSession
    ):
        """만료된 토큰으로 시도 - 400 에러"""
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": reset_token, "new_password": "NewStrongPass123!"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_password_reset_confirm_invalid_token(
        self, async_client: AsyncClient
    ):
        """존재하지 않는 토큰 - 400 에러"""
        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "invalid-token-xyz", "new_password": "NewStrongPass123!"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_password_reset_confirm_weak_password(
        self, async_client: AsyncClient, test_user: User, test_db: AsyncSession
    ):
        """약한 비밀번호로 재설정 시도 - 400 에러"""
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": reset_token, "new_password": "weak"},
        )

        # Pydantic min_length=8 또는 validate_password에서 에러
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_password_reset_clears_account_lock(
        self, async_client: AsyncClient, test_user: User, test_db: AsyncSession
    ):
        """비밀번호 재설정 시 계정 잠금 해제 확인"""
        reset_token = secrets.token_urlsafe(32)
        test_user.password_reset_token = reset_token
        test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        test_user.failed_login_attempts = 5
        test_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": reset_token, "new_password": "NewStrongPass123!"},
        )

        assert response.status_code == 200
        await test_db.refresh(test_user)
        assert test_user.failed_login_attempts == 0
        assert test_user.locked_until is None
