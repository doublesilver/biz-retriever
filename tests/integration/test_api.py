"""
API 엔드포인트 통합 테스트
"""
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    """헬스 체크 엔드포인트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_register_user():
    """사용자 등록"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "StrongPass123!"
            }
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_register_weak_password():
    """약한 비밀번호로 등록 시도"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test2@example.com",
                "password": "weak"  # 조건 미달
            }
        )
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_swagger_docs():
    """Swagger 문서 접근"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200
