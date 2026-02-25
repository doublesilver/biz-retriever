"""
WebSocket 엔드포인트 통합 테스트
- 유효한 토큰으로 연결
- 유효하지 않은 토큰으로 연결 실패
- 토큰 없이 연결 시도
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.endpoints.websocket import websocket_endpoint
from app.core.websocket import ConnectionManager


class TestWebSocketEndpoint:
    """websocket_endpoint 테스트"""

    async def test_invalid_token_closes_connection(self):
        """유효하지 않은 토큰 -> WS 1008 닫기"""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("app.api.endpoints.websocket.get_current_user_from_token",
                    AsyncMock(return_value=None)):
            await websocket_endpoint(websocket=mock_ws, token="invalid-token")

        mock_ws.accept.assert_awaited_once()
        mock_ws.close.assert_awaited_once()

    async def test_valid_token_connects_then_disconnect(self):
        """유효한 토큰 -> 연결 후 WebSocketDisconnect 처리"""
        from starlette.websockets import WebSocketDisconnect

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        mock_user = MagicMock()
        mock_user.id = 1

        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = MagicMock()

        with patch("app.api.endpoints.websocket.get_current_user_from_token",
                    AsyncMock(return_value=mock_user)):
            with patch("app.api.endpoints.websocket.manager", mock_manager):
                await websocket_endpoint(websocket=mock_ws, token="valid-token")

        mock_manager.connect.assert_awaited_once_with(mock_ws)
        mock_manager.disconnect.assert_called_once_with(mock_ws)

    async def test_exception_closes_with_error(self):
        """인증 중 예외 -> WS 1011 닫기"""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("app.api.endpoints.websocket.get_current_user_from_token",
                    AsyncMock(side_effect=Exception("Auth error"))):
            await websocket_endpoint(websocket=mock_ws, token="bad-token")

        mock_ws.close.assert_awaited_once()

    async def test_exception_close_fails_silently(self):
        """close 중 예외도 무시"""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock(side_effect=Exception("Already closed"))

        with patch("app.api.endpoints.websocket.get_current_user_from_token",
                    AsyncMock(side_effect=Exception("Auth error"))):
            # Should not raise
            await websocket_endpoint(websocket=mock_ws, token="bad-token")
