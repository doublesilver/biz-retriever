"""
Auth API 확장 통합 테스트
- 회원가입, 로그인, 토큰 갱신, 로그아웃
- 계정 잠금 (5회 실패)
- 이메일 중복 확인
- 비밀번호 재설정
- 이메일 인증
"""

from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models import User


class TestRegister:
    """회원가입"""

    async def test_register_success(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "SecurePass123!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": test_user.email, "password": "SecurePass123!"},
        )
        assert response.status_code == 400

    async def test_register_weak_password(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "123"},
        )
        assert response.status_code == 422  # Pydantic min_length=8

    async def test_register_no_uppercase(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak2@example.com", "password": "nouppercasepass1!"},
        )
        assert response.status_code == 400


class TestLogin:
    """로그인"""

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": test_user.email, "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: User):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": test_user.email, "password": "WrongPass123!"},
        )
        assert response.status_code == 400

    async def test_login_nonexistent_user(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "noone@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 400

    async def test_login_inactive_user(self, async_client: AsyncClient, test_db: AsyncSession):
        user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=False,
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "inactive@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 400


class TestAccountLocking:
    """계정 잠금"""

    async def test_lock_after_5_failures(self, async_client: AsyncClient, test_db: AsyncSession):
        user = User(
            email="lockme@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login/access-token",
                data={"username": "lockme@example.com", "password": "Wrong123!"},
            )

        # 5th attempt should lock
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "lockme@example.com", "password": "Wrong123!"},
        )
        assert response.status_code == 400
        assert (
            "locked" in response.json().get("error", {}).get("message", "").lower()
            or "locked" in response.json().get("detail", "").lower()
        )


class TestCheckEmail:
    """이메일 중복 확인"""

    async def test_email_available(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.get(
            "/api/v1/auth/check-email",
            params={"email": "available@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["exists"] is False

    async def test_email_taken(self, async_client: AsyncClient, test_user: User):
        response = await async_client.get(
            "/api/v1/auth/check-email",
            params={"email": test_user.email},
        )
        assert response.status_code == 200
        assert response.json()["exists"] is True


class TestRefreshToken:
    """토큰 갱신"""

    async def test_refresh_success(self, async_client: AsyncClient, test_user: User):
        # 먼저 로그인
        login_resp = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": test_user.email, "password": "TestPass123!"},
        )
        tokens = login_resp.json()

        # refresh
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogout:
    """로그아웃"""

    async def test_logout_success(self, authenticated_client: AsyncClient):
        response = await authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200

    async def test_logout_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestGetUsers:
    """사용자 목록 조회"""

    async def test_get_users_authenticated(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/api/v1/auth/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_users_unauthenticated(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/auth/users")
        assert response.status_code == 401


class TestPasswordReset:
    """비밀번호 재설정"""

    async def test_request_reset(self, async_client: AsyncClient, test_user: User):
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": test_user.email},
        )
        assert response.status_code == 200
        # 항상 동일한 응답 (이메일 존재 여부 비노출)
        assert "message" in response.json()

    async def test_request_reset_nonexistent(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200

    async def test_confirm_reset_invalid_token(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "invalid_token", "new_password": "NewSecure123!"},
        )
        assert response.status_code == 400


class TestPasswordResetConfirmValid:
    """비밀번호 재설정 확인 (유효 토큰)"""

    async def test_confirm_reset_success(self, async_client: AsyncClient, test_db: AsyncSession):
        """유효 토큰으로 비밀번호 재설정 성공"""
        user = User(
            email="resetme@example.com",
            hashed_password=get_password_hash("OldPass123!"),
            is_active=True,
            password_reset_token="valid-reset-token-abc",
            password_reset_expires=datetime.utcnow() + timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "valid-reset-token-abc", "new_password": "NewSecure456!"},
        )
        assert response.status_code == 200
        assert (
            "reset successfully" in response.json()["message"].lower() or "reset" in response.json()["message"].lower()
        )

    async def test_confirm_reset_expired_token(self, async_client: AsyncClient, test_db: AsyncSession):
        """만료된 토큰으로 비밀번호 재설정 실패"""
        user = User(
            email="expired_reset@example.com",
            hashed_password=get_password_hash("OldPass123!"),
            is_active=True,
            password_reset_token="expired-token-xyz",
            password_reset_expires=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "expired-token-xyz", "new_password": "NewSecure456!"},
        )
        assert response.status_code == 400

    async def test_confirm_reset_weak_new_password(self, async_client: AsyncClient, test_db: AsyncSession):
        """유효 토큰이지만 약한 새 비밀번호"""
        user = User(
            email="weaknew@example.com",
            hashed_password=get_password_hash("OldPass123!"),
            is_active=True,
            password_reset_token="weak-pass-token",
            password_reset_expires=datetime.utcnow() + timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "weak-pass-token", "new_password": "nouppercase1!"},
        )
        assert response.status_code == 400


class TestAccountLockExpiry:
    """계정 잠금 만료"""

    async def test_login_after_lock_expired(self, async_client: AsyncClient, test_db: AsyncSession):
        """잠금 만료 후 로그인 성공"""
        user = User(
            email="lock_expired@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            failed_login_attempts=5,
            locked_until=datetime.utcnow() - timedelta(minutes=1),  # 이미 만료
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "lock_expired@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestEmailVerification:
    """이메일 인증"""

    async def test_verify_invalid_token(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid_token"},
        )
        assert response.status_code == 400

    async def test_verify_valid_token(self, async_client: AsyncClient, test_db: AsyncSession):
        """유효 토큰으로 이메일 인증 성공"""
        user = User(
            email="verify_me@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token="valid-verify-token",
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "valid-verify-token"},
        )
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    async def test_verify_already_verified(self, async_client: AsyncClient, test_db: AsyncSession):
        """이미 인증된 이메일"""
        user = User(
            email="already_verified@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=True,
            email_verification_token="already-done-token",
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "already-done-token"},
        )
        assert response.status_code == 200
        assert "already" in response.json()["message"].lower()

    async def test_verify_expired_token(self, async_client: AsyncClient, test_db: AsyncSession):
        """만료된 인증 토큰"""
        user = User(
            email="expired_verify@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token="expired-verify-token",
            email_verification_expires=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "expired-verify-token"},
        )
        assert response.status_code == 400

    async def test_resend_verification(self, async_client: AsyncClient, test_db: AsyncSession):
        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200

    async def test_resend_verification_real_user(self, async_client: AsyncClient, test_db: AsyncSession):
        """미인증 사용자에게 인증 메일 재발송"""
        user = User(
            email="resend_me@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "resend_me@example.com"},
        )
        assert response.status_code == 200
