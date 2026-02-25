"""
ConnectionManager 단위 테스트
- connect, disconnect, broadcast
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.websocket import ConnectionManager


class TestConnectionManager:
    """ConnectionManager 테스트"""

    async def test_connect(self):
        """연결 수락 및 리스트 추가"""
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect(ws)
        assert ws in mgr.active_connections
        ws.accept.assert_awaited_once()

    async def test_disconnect(self):
        """연결 해제"""
        mgr = ConnectionManager()
        ws = AsyncMock()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        assert ws not in mgr.active_connections

    async def test_disconnect_not_in_list(self):
        """리스트에 없는 연결 해제 시 에러 없음"""
        mgr = ConnectionManager()
        ws = AsyncMock()
        mgr.disconnect(ws)  # Should not raise

    async def test_broadcast_no_connections(self):
        """연결 없으면 early return"""
        mgr = ConnectionManager()
        await mgr.broadcast("test")  # Should not raise

    async def test_broadcast_success(self):
        """모든 연결에 메시지 전송"""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        mgr.active_connections = [ws1, ws2]
        await mgr.broadcast("hello")
        ws1.send_text.assert_awaited_once_with("hello")
        ws2.send_text.assert_awaited_once_with("hello")

    async def test_broadcast_error_disconnects(self):
        """전송 실패 시 해당 연결 제거"""
        mgr = ConnectionManager()
        ws_ok = AsyncMock()
        ws_fail = AsyncMock()
        ws_fail.send_text.side_effect = Exception("Connection lost")
        mgr.active_connections = [ws_ok, ws_fail]
        await mgr.broadcast("hello")
        ws_ok.send_text.assert_awaited_once()
        assert ws_fail not in mgr.active_connections
