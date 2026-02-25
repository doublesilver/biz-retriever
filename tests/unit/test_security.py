"""
보안 기능 단위 테스트
"""

import pytest

from app.core.exceptions import WeakPasswordError
from app.core.security import (get_password_hash, validate_password,
                               verify_password)


def test_validate_password_strong():
    """강한 비밀번호 검증 - 통과"""
    # 모든 조건 만족
    validate_password("StrongPass123!")
    # 예외가 발생하지 않으면 성공


def test_validate_password_too_short():
    """비밀번호 길이 부족"""
    with pytest.raises(WeakPasswordError, match="최소 8자"):
        validate_password("Short1!")


def test_validate_password_no_uppercase():
    """대문자 없음"""
    with pytest.raises(WeakPasswordError, match="대문자"):
        validate_password("lowercase123!")


def test_validate_password_no_lowercase():
    """소문자 없음"""
    with pytest.raises(WeakPasswordError, match="소문자"):
        validate_password("UPPERCASE123!")


def test_validate_password_no_digit():
    """숫자 없음"""
    with pytest.raises(WeakPasswordError, match="숫자"):
        validate_password("NoDigits!")


def test_validate_password_no_special():
    """특수문자 없음"""
    with pytest.raises(WeakPasswordError, match="특수문자"):
        validate_password("NoSpecial123")


def test_password_hashing():
    """비밀번호 해싱 및 검증"""
    password = "TestPassword123!"
    hashed = get_password_hash(password)

    # 해시된 값은 원본과 다름
    assert hashed != password

    # 검증은 성공
    assert verify_password(password, hashed) == True

    # 잘못된 비밀번호는 실패
    assert verify_password("WrongPassword", hashed) == False
