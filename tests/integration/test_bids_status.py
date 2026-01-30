import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_update_bid_status(authenticated_client: AsyncClient, sample_bid):
    """
    Test updating bid status via PATCH /bids/{id}
    """
    update_data = {"status": "reviewing", "notes": "Checking details"}

    response = await authenticated_client.patch(
        f"/api/v1/bids/{sample_bid.id}", json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reviewing"
    assert data["notes"] == "Checking details"
    assert data["id"] == sample_bid.id


@pytest.mark.asyncio
async def test_update_bid_assigned_to(
    authenticated_client: AsyncClient, sample_bid, test_user
):
    """
    Test assigning a bid to a user
    """
    update_data = {"assigned_to": test_user.id}

    response = await authenticated_client.patch(
        f"/api/v1/bids/{sample_bid.id}", json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["assigned_to"] == test_user.id


@pytest.mark.asyncio
async def test_update_bid_not_found(authenticated_client: AsyncClient):
    """
    Test updating non-existent bid
    """
    response = await authenticated_client.patch(
        "/api/v1/bids/999999", json={"status": "completed"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_bid_unauthorized(async_client: AsyncClient, sample_bid):
    """
    Test updating without auth
    """
    response = await async_client.patch(
        f"/api/v1/bids/{sample_bid.id}", json={"status": "completed"}
    )
    assert response.status_code == 401
