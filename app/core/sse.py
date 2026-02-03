"""
Server-Sent Events (SSE) Manager for Serverless

Replaces WebSocket for real-time notifications in Vercel environment.
WebSocket requires persistent connections (not supported in serverless).
SSE is one-way (server->client) but works with HTTP and is stateless.
"""

import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi.responses import StreamingResponse

from app.core.logging import logger


class SSEManager:
    """
    Server-Sent Events manager for serverless environments.

    Unlike WebSocket ConnectionManager, this is STATELESS:
    - No global connection list (each request is independent)
    - Uses database/Redis for message broadcasting
    - Works within Vercel's 60-second timeout
    """

    def __init__(self, heartbeat_interval: int = 15):
        """
        Initialize SSE manager.

        Args:
            heartbeat_interval: Seconds between heartbeat pings (default 15s)
        """
        self.heartbeat_interval = heartbeat_interval

    async def event_stream(
        self,
        user_id: int,
        last_event_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate SSE event stream for a user.

        Args:
            user_id: User ID for filtering events
            last_event_id: Resume from this event ID (for reconnection)

        Yields:
            SSE-formatted strings: "data: {json}\\n\\n"
        """
        logger.info(f"SSE stream started for user {user_id}")

        try:
            # Track start time (Vercel 60s timeout)
            start_time = asyncio.get_event_loop().time()
            last_heartbeat = start_time

            while True:
                current_time = asyncio.get_event_loop().time()

                # Safety: Exit before Vercel timeout (50s safety margin)
                if current_time - start_time > 50:
                    logger.info(
                        f"SSE stream timeout approaching, closing for user {user_id}"
                    )
                    yield self._format_event(
                        {"type": "timeout", "message": "Reconnecting..."}
                    )
                    break

                # Send heartbeat to keep connection alive
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    yield f": heartbeat {datetime.utcnow().isoformat()}\n\n"
                    last_heartbeat = current_time

                # TODO: Query database/Redis for new events for this user
                # For now, this is a placeholder implementation
                # In production, check:
                # - New bid announcements matching user's keywords
                # - AI analysis completion (Job+Polling results)
                # - System notifications

                # Example: Check for messages (replace with actual implementation)
                # message = await self._get_next_message(user_id, last_event_id)
                # if message:
                #     yield self._format_event(message.dict(), event_id=message.id)
                #     last_event_id = message.id

                # Sleep to avoid busy-waiting
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"SSE stream error for user {user_id}: {e}")
            yield self._format_event({"type": "error", "message": str(e)})

    def _format_event(
        self,
        data: dict,
        event_type: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> str:
        """
        Format data as SSE event string.

        Args:
            data: Data to serialize as JSON
            event_type: Optional event type (e.g., "notification", "bid")
            event_id: Optional event ID for reconnection tracking

        Returns:
            SSE-formatted string
        """
        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        if event_type:
            lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")  # Empty line to terminate event
        return "\n".join(lines) + "\n"


def create_sse_stream(
    user_id: int,
    last_event_id: Optional[str] = None,
) -> StreamingResponse:
    """
    Create SSE StreamingResponse for endpoint.

    Usage in endpoint:
        @router.get("/stream")
        async def stream_events(current_user: User = Depends(get_current_user)):
            return create_sse_stream(current_user.id)

    Args:
        user_id: User ID for event filtering
        last_event_id: Resume from this event ID

    Returns:
        StreamingResponse with SSE headers
    """
    manager = SSEManager()

    return StreamingResponse(
        manager.event_stream(user_id, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
