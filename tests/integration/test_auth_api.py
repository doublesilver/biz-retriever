"""
Auth API 통합 테스트
- 로그인 / 회원가입 / 토큰 갱신 / 로그아웃
- 계정 잠금 / 비밀번호 재설정 / 이메일 인증

NOTE: 에러 응답은 ApiResponse envelope 형식:
  {"success": false, "error": {"code": "...", "message": "..."}, "timestamp": "..."}
"""

import pytest
import secrets
from datetime import datetime, timedelta
from unittest.mock import patch

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.db.models import User


def get_error_message(response):
    """에러 응답에서 메시지 추출 (envelope 또는 legacy 형식)"""
    data = response.json()
    if "error" in data and isinstance(data["error"], dict):
        return data["error"].get("message", "")
    return data.get("detail", "")


class TestRegisterAPI:
    """회원가입 API 테스트"""

    async def test_register_success(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_weak_password(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "weak"},
        )
        assert response.status_code in [400, 422]

    async def test_register_no_uppercase(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "nouppercase1!"},
        )
        assert response.status_code == 400

    async def test_register_duplicate_email(self, async_client, test_user):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == 400
        msg = get_error_message(response)
        assert "already exists" in msg


class TestLoginAPI:
    """로그인 API 테스트"""

    async def test_login_success(self, async_client, test_user):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "test@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client, test_user):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "test@example.com", "password": "WrongPass123!"},
        )
        assert response.status_code == 400
        msg = get_error_message(response)
        assert "Incorrect" in msg

    async def test_login_nonexistent_user(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "nobody@example.com", "password": "Pass123!"},
        )
        assert response.status_code == 400

    async def test_login_inactive_user(self, async_client, test_db):
        """비활성 사용자 로그인 차단"""
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
        msg = get_error_message(response)
        assert "Inactive" in msg or "inactive" in msg.lower()


class TestAccountLocking:
    """계정 잠금 테스트"""

    async def test_failed_attempts_increment(self, async_client, test_user, test_db):
        """연속 실패 시 시도 횟수 증가"""
        for i in range(3):
            await async_client.post(
                "/api/v1/auth/login/access-token",
                data={"username": "test@example.com", "password": "Wrong123!"},
            )

        await test_db.refresh(test_user)
        assert test_user.failed_login_attempts == 3

    async def test_account_locks_after_5_failures(self, async_client, test_user, test_db):
        """5회 실패 후 계정 잠금"""
        for i in range(5):
            response = await async_client.post(
                "/api/v1/auth/login/access-token",
                data={"username": "test@example.com", "password": "Wrong123!"},
            )

        assert response.status_code == 400
        msg = get_error_message(response)
        assert "locked" in msg.lower()

        await test_db.refresh(test_user)
        assert test_user.locked_until is not None

    async def test_locked_account_rejected(self, async_client, test_user, test_db):
        """잠긴 계정은 올바른 비밀번호도 거부"""
        test_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        test_user.failed_login_attempts = 5
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "test@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 400
        msg = get_error_message(response)
        assert "locked" in msg.lower()

    async def test_lock_expires(self, async_client, test_user, test_db):
        """잠금 시간 만료 후 로그인 가능"""
        test_user.locked_until = datetime.utcnow() - timedelta(minutes=1)
        test_user.failed_login_attempts = 5
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "test@example.com", "password": "TestPass123!"},
        )
        assert response.status_code == 200


class TestRefreshTokenAPI:
    """토큰 갱신 API 테스트"""

    async def test_refresh_success(self, async_client, test_user):
        refresh_token = create_refresh_token(test_user.email)
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_with_access_token_fails(self, async_client, test_user):
        access_token = create_access_token(test_user.email)
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401

    async def test_refresh_with_invalid_token(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401


class TestLogoutAPI:
    """로그아웃 API 테스트"""

    async def test_logout_success(self, authenticated_client):
        response = await authenticated_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        # 성공 응답은 envelope이 아닌 직접 반환
        assert data.get("message") == "Successfully logged out"

    async def test_logout_without_auth(self, async_client):
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestCheckEmailAPI:
    """이메일 중복 확인 API"""

    async def test_email_exists(self, async_client, test_user):
        response = await async_client.get(
            "/api/v1/auth/check-email",
            params={"email": "test@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["exists"] is True

    async def test_email_available(self, async_client, test_db):
        response = await async_client.get(
            "/api/v1/auth/check-email",
            params={"email": "available@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["exists"] is False


class TestReadUsersAPI:
    """사용자 목록 조회 API"""

    async def test_requires_auth(self, async_client):
        response = await async_client.get("/api/v1/auth/users")
        assert response.status_code == 401

    async def test_returns_users(self, authenticated_client, test_user):
        response = await authenticated_client.get("/api/v1/auth/users")
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1


class TestPasswordResetAPI:
    """비밀번호 재설정 API"""

    async def test_request_always_200(self, async_client, test_db):
        """이메일 존재 여부와 무관하게 200"""
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200

    async def test_request_existing_user(self, async_client, test_user, test_db):
        response = await async_client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

        await test_db.refresh(test_user)
        assert test_user.password_reset_token is not None

    async def test_confirm_success(self, async_client, test_user, test_db):
        """비밀번호 재설정 성공"""
        token = secrets.token_urlsafe(32)
        test_user.password_reset_token = token
        test_user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": token, "new_password": "NewStrongPass123!"},
        )
        assert response.status_code == 200

    async def test_confirm_invalid_token(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": "invalid_token", "new_password": "NewStrongPass123!"},
        )
        assert response.status_code == 400

    async def test_confirm_expired_token(self, async_client, test_user, test_db):
        """만료된 토큰"""
        token = secrets.token_urlsafe(32)
        test_user.password_reset_token = token
        test_user.password_reset_expires = datetime.utcnow() - timedelta(hours=1)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={"token": token, "new_password": "NewStrongPass123!"},
        )
        assert response.status_code == 400


class TestEmailVerificationAPI:
    """이메일 인증 API"""

    async def test_verify_success(self, async_client, test_db):
        token = secrets.token_urlsafe(32)
        user = User(
            email="verify@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token=token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200

    async def test_verify_invalid_token(self, async_client, test_db):
        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid_token"},
        )
        assert response.status_code == 400

    async def test_verify_already_verified(self, async_client, test_db):
        token = secrets.token_urlsafe(32)
        user = User(
            email="already@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=True,
            email_verification_token=token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 200
        assert "already" in response.json().get("message", "").lower()

    async def test_verify_expired_token(self, async_client, test_db):
        token = secrets.token_urlsafe(32)
        user = User(
            email="expired@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
            email_verification_token=token,
            email_verification_expires=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/verify-email",
            json={"token": token},
        )
        assert response.status_code == 400

    async def test_resend_verification(self, async_client, test_db):
        user = User(
            email="resend@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_email_verified=False,
        )
        test_db.add(user)
        await test_db.commit()

        response = await async_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "resend@example.com"},
        )
        assert response.status_code == 200
