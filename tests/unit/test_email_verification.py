"""
이메일 인증 기능 테스트
- verify-email: 인증 토큰으로 이메일 인증
- resend-verification: 인증 이메일 재발송
- 회원가입 시 인증 토큰 생성 확인
"""

import secrets
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models import User


class TestEmailVerification:
    """이메일 인증 (POST /auth/verify-email)"""

    @pytest.mark.asyncio
    async def test_verify_email_valid_token(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """유효한 토큰으로 이메일 인증 - 성공"""
        # Setup: 인증되지 않은 사용자 생성
        verification_token = secrets.token_urlsafe(32)
        user = User(
            email="unverified@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token=verification_token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

        # DB 확인
        await test_db.refresh(user)
        assert user.is_email_verified is True
        assert user.email_verification_token is None

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """만료된 토큰으로 인증 시도 - 400 에러"""
        verification_token = secrets.token_urlsafe(32)
        user = User(
            email="expired@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token=verification_token,
            email_verification_expires=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """존재하지 않는 토큰 - 400 에러"""
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "nonexistent-token-xyz"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """이미 인증된 사용자 - 성공 응답 (멱등)"""
        verification_token = secrets.token_urlsafe(32)
        user = User(
            email="alreadyverified@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=True,
            email_verification_token=verification_token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": verification_token},
        )

        assert response.status_code == 200
        assert "already" in response.json()["message"].lower()


class TestResendVerification:
    """인증 이메일 재발송 (POST /auth/resend-verification)"""

    @pytest.mark.asyncio
    async def test_resend_verification_unverified_user(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """인증되지 않은 사용자 - 재발송 성공"""
        user = User(
            email="resend-test@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
        )
        test_db.add(user)
        await test_db.commit()

        with patch("app.api.endpoints.auth.email_service") as mock_email:
            mock_email.is_configured.return_value = False
            response = await async_client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "resend-test@example.com"},
            )

        assert response.status_code == 200

        # 새 토큰이 생성되었는지 확인
        await test_db.refresh(user)
        assert user.email_verification_token is not None
        assert user.email_verification_expires is not None

    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_user(
        self, async_client: AsyncClient
    ):
        """존재하지 않는 사용자 - 동일한 성공 응답 (Enumeration 방지)"""
        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@example.com"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """이미 인증된 사용자 - 성공 응답 (토큰 미발급)"""
        user = User(
            email="verified-resend@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "verified-resend@example.com"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resend_verification_invalid_email(
        self, async_client: AsyncClient
    ):
        """잘못된 이메일 형식 - 422 Validation Error"""
        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "not-valid"},
        )

        assert response.status_code == 422


class TestRegistrationWithVerification:
    """회원가입 시 이메일 인증 토큰 생성 확인"""

    @pytest.mark.asyncio
    async def test_register_creates_verification_token(
        self, async_client: AsyncClient, test_db: AsyncSession
    ):
        """회원가입 시 인증 토큰이 생성되는지 확인"""
        with patch("app.api.endpoints.auth.email_service") as mock_email:
            mock_email.is_configured.return_value = False
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newverify@example.com",
                    "password": "StrongPass123!",
                },
            )

        assert response.status_code in [200, 201]

        # DB에서 사용자 확인
        from sqlalchemy import select

        result = await test_db.execute(
            select(User).where(User.email == "newverify@example.com")
        )
        user = result.scalars().first()

        assert user is not None
        assert user.is_email_verified is False
        assert user.email_verification_token is not None
        assert user.email_verification_expires is not None
