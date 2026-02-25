from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.api.endpoints.websocket import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


@pytest.mark.asyncio
async def test_debug_ws_no_token():
    with patch(
        "app.api.endpoints.websocket.get_current_user_from_token",
        new_callable=AsyncMock,
    ) as mock_auth:
        mock_auth.return_value = None

        with pytest.raises(WebSocketDisconnect) as e:
            with client.websocket_connect("/notifications?token=invalid") as websocket:
                websocket.receive_text()

        print(f"DEBUG: Code={e.value.code}")
        assert e.value.code == 1008
