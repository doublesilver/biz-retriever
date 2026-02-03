"""
Server-Sent Events (SSE) Endpoint

Replaces WebSocket for real-time notifications in serverless environments.
SSE is one-way (server->client) but works with HTTP and is stateless.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header

from app.api import deps
from app.core.logging import logger
from app.core.sse import create_sse_stream
from app.db.models import User

router = APIRouter()


@router.get("/stream")
async def stream_events(
    current_user: User = Depends(deps.get_current_user),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    """
    SSE 스트리밍 엔드포인트 - 실시간 알림용

    WebSocket 대체 방식으로 서버리스 환경에서도 동작합니다.
    클라이언트는 EventSource API를 사용하여 연결합니다.

    **사용 예시 (JavaScript):**
    ```javascript
    const token = 'your_jwt_token';
    const eventSource = new EventSource(
        `/api/v1/realtime/stream`,
        { headers: { 'Authorization': `Bearer ${token}` } }
    );

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
    };

    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();
    };
    ```

    **이벤트 타입:**
    - `heartbeat`: 연결 유지용 ping (15초 간격)
    - `notification`: 새 알림
    - `bid`: 새 입찰 공고
    - `timeout`: 연결 시간 초과 (재연결 필요)
    - `error`: 오류 발생

    **헤더:**
    - `Authorization`: Bearer {access_token}
    - `Last-Event-ID`: 마지막으로 받은 이벤트 ID (재연결 시)

    **응답 형식:**
    ```
    data: {"type": "notification", "message": "새 입찰 공고"}

    : heartbeat 2026-01-31T10:30:00

    ```

    **제한사항:**
    - Vercel 환경에서는 60초 타임아웃 (50초 후 자동 종료)
    - 재연결 시 Last-Event-ID 헤더로 이어받기 가능
    """
    logger.info(f"SSE stream requested by user {current_user.id}")

    return create_sse_stream(
        user_id=current_user.id,
        last_event_id=last_event_id,
    )
