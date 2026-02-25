import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.keyword_service import keyword_service


@pytest.mark.asyncio
async def test_add_keyword(authenticated_client: AsyncClient, test_db: AsyncSession):
    response = await authenticated_client.post("/api/v1/filters/keywords", json={"keyword": "test_exclude"})
    assert response.status_code == 200
    assert "추가되었습니다" in response.json()["message"]

    # Verify DB
    keywords = await keyword_service.get_active_keywords(test_db)
    assert "test_exclude" in keywords


@pytest.mark.asyncio
async def test_add_duplicate_keyword(authenticated_client: AsyncClient, test_db: AsyncSession):
    await authenticated_client.post("/api/v1/filters/keywords", json={"keyword": "duplicate"})

    response = await authenticated_client.post("/api/v1/filters/keywords", json={"keyword": "duplicate"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_keywords(authenticated_client: AsyncClient, test_db: AsyncSession):
    await keyword_service.create_keyword(test_db, "kw1")
    await keyword_service.create_keyword(test_db, "kw2")

    response = await authenticated_client.get("/api/v1/filters/keywords")
    assert response.status_code == 200
    data = response.json()
    assert "kw1" in data["keywords"]
    assert "kw2" in data["keywords"]


@pytest.mark.asyncio
async def test_delete_keyword(authenticated_client: AsyncClient, test_db: AsyncSession):
    await keyword_service.create_keyword(test_db, "to_delete")

    response = await authenticated_client.delete("/api/v1/filters/keywords/to_delete")
    assert response.status_code == 200

    keywords = await keyword_service.get_active_keywords(test_db)
    assert "to_delete" not in keywords


@pytest.mark.asyncio
async def test_delete_non_existent(authenticated_client: AsyncClient):
    response = await authenticated_client.delete("/api/v1/filters/keywords/unknown")
    assert response.status_code == 404
