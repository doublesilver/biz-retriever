"""
API 엔드포인트 통합 테스트
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """헬스 체크 엔드포인트"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """사용자 등록"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """약한 비밀번호로 등록 시도"""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "test2@example.com", "password": "weak"},  # 조건 미달
    )
    # Pydantic validation error는 422 반환
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_swagger_docs(async_client: AsyncClient):
    """Swagger 문서 접근"""
    response = await async_client.get("/docs")
    assert response.status_code == 200
