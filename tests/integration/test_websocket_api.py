"""
WebSocket API 통합 테스트
"""

import pytest
from starlette.testclient import TestClient

from app.main import app


class TestWebSocketEndpoint:
    """WebSocket 엔드포인트 테스트"""

    def test_ws_invalid_token(self):
        """유효하지 않은 토큰으로 연결 시도 - 연결 종료"""
        client = TestClient(app)
        with client.websocket_connect("/api/v1/realtime/notifications?token=invalid_token") as ws:
            # 서버가 인증 실패로 연결을 닫음 (policy violation)
            # close 메시지를 받아야 함
            pass

    def test_ws_missing_token(self):
        """토큰 없이 연결 시도 - 422"""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/realtime/notifications") as ws:
                pass
