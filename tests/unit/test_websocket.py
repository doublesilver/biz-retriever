import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.websocket import manager
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def mock_token():
    return create_access_token(subject="test@example.com")

@pytest.mark.asyncio
async def test_websocket_connection_success():
    with patch("app.api.endpoints.websocket.get_current_user_from_token", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = {"email": "test@example.com"} # Mock user object
        
        with client.websocket_connect(f"/ws/notifications?token=valid_token") as websocket:
            assert len(manager.active_connections) == 1
            websocket.send_text("Hello")
        
        assert len(manager.active_connections) == 0

@pytest.mark.asyncio
async def test_websocket_connection_no_token():
    # Test missing token param (FastAPI raises 422 or 403) or invalid token logic
    # If token is required query param, missing it raises 422 Validation Error
    with pytest.raises(WebSocketDisconnect) as e:
         with client.websocket_connect("/ws/notifications?token=invalid_token") as websocket:
             pass
    # If token is invalid, your code closes with 1008
    # However, we need to ensure get_current_user_from_token returns None
    
    with patch("app.api.endpoints.websocket.get_current_user_from_token", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = None
        with pytest.raises(WebSocketDisconnect) as e:
            with client.websocket_connect("/ws/notifications?token=invalid_token") as websocket:
                websocket.receive_text() # Trigger read to get close frame
        assert e.value.code in [1000, 1008]

@pytest.mark.asyncio
async def test_websocket_broadcast():
    # We need to simulate multiple connections. 
    # Since TestClient is sync, testing async broadcast specifically might need 'async_client' or mocking.
    # Here we mock the manager's broadcast to verify it calls send_text on active connections.
    
    mock_ws = AsyncMock()
    manager.active_connections.append(mock_ws)
    
    await manager.broadcast("Test Message")
    
    mock_ws.send_text.assert_called_with("Test Message")
    
    manager.active_connections.remove(mock_ws)

@pytest.mark.asyncio
async def test_websocket_broadcast_disconnect_on_error():
    mock_ws = AsyncMock()
    mock_ws.send_text.side_effect = Exception("Connection Error")
    manager.active_connections.append(mock_ws)
    
    # Broadcast should fail for this client and remove it
    await manager.broadcast("Test Message")
    
    assert mock_ws not in manager.active_connections
