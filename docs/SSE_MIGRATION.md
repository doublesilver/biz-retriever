# WebSocket → SSE Migration

## Why SSE Instead of WebSocket?

**Problem**: Vercel serverless functions don't support WebSocket (requires persistent connections).

**Solution**: Server-Sent Events (SSE) - HTTP-based one-way streaming from server to client.

## Architecture Differences

| Feature | WebSocket | SSE |
|---------|-----------|-----|
| **Direction** | Bidirectional | Server → Client only |
| **Protocol** | ws:// (upgrade from HTTP) | HTTP |
| **Serverless** | ❌ Not supported | ✅ Supported |
| **Reconnection** | Manual | Automatic (browser) |
| **Timeout** | Persistent | Subject to function timeout |
| **Binary data** | ✅ Supported | ❌ Text only |
| **Connection limit** | Browser limit ~6 | Browser limit ~6 |

## Implementation

### Before (WebSocket)
```python
# app/core/websocket.py
class ConnectionManager:
    def __init__(self):
        self.active_connections = []  # In-memory (lost on restart)
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
```

### After (SSE)
```python
# app/core/sse.py
class SSEManager:
    """Stateless - no in-memory connection list"""
    
    async def event_stream(self, user_id: int):
        while True:
            # Query DB/Redis for new events (stateless)
            # Send heartbeat every 15s
            yield f": heartbeat\n\n"
            
            # Exit before 60s timeout
            if elapsed > 50:
                yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
                break
            
            await asyncio.sleep(1)

def create_sse_stream(user_id: int) -> StreamingResponse:
    return StreamingResponse(
        SSEManager().event_stream(user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )
```

## Client-Side Changes (Frontend)

### Before (WebSocket)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications?token=xxx');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log(event.data);
ws.onerror = (error) => console.error('Error:', error);
ws.onclose = () => {
    // Manual reconnection logic needed
    setTimeout(() => connectWebSocket(), 3000);
};
```

### After (SSE)
```javascript
const eventSource = new EventSource('/api/v1/realtime/stream', {
    // Note: EventSource doesn't support custom headers
    // Use query param for auth: /stream?token=xxx
});

eventSource.onopen = () => console.log('Connected');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    // Handle timeout event (server closing before 60s)
    if (data.type === 'timeout') {
        // Browser will auto-reconnect
        console.log('Reconnecting...');
    }
};

eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    // Browser automatically reconnects on error
};

// Listen for specific event types
eventSource.addEventListener('bid', (event) => {
    const bid = JSON.parse(event.data);
    showBidNotification(bid);
});

eventSource.addEventListener('analysis', (event) => {
    const result = JSON.parse(event.data);
    updateAnalysisStatus(result);
});

// Clean up
window.addEventListener('beforeunload', () => eventSource.close());
```

### With JWT Token (Workaround)
Since EventSource doesn't support custom headers, pass token via query param:

```javascript
function createAuthenticatedSSE() {
    const token = localStorage.getItem('access_token');
    const url = `/api/v1/realtime/stream?token=${encodeURIComponent(token)}`;
    return new EventSource(url);
}

// Handle token refresh
function reconnectWithNewToken() {
    eventSource.close();
    // Get new token via refresh endpoint
    refreshToken().then(() => {
        eventSource = createAuthenticatedSSE();
    });
}
```

## SSE Event Format

### Server-side format
```python
# Simple message
yield f"data: {json.dumps({'message': 'Hello'})}\n\n"

# With event type
yield f"event: bid\ndata: {json.dumps(bid)}\n\n"

# With ID (for reconnection)
yield f"id: 123\ndata: {json.dumps(data)}\n\n"

# Heartbeat (comment line, ignored by client)
yield f": heartbeat {timestamp}\n\n"
```

### Client receives
```javascript
event.data    // JSON string
event.type    // 'message' (default) or custom event type
event.lastEventId  // ID for reconnection via Last-Event-ID header
```

## Limitations & Workarounds

| Limitation | Workaround |
|------------|------------|
| **60s timeout** | Close at 50s, browser auto-reconnects with `Last-Event-ID` |
| **One-way only** | Client uses regular API calls for actions (POST/PUT) |
| **No broadcast** | Use DB/Redis as message queue, each connection polls |
| **No binary** | Base64 encode if needed (not recommended) |
| **Auth header** | Pass JWT via query param `?token=xxx` |

## Serverless Timeout Handling

```
Timeline (Vercel Function):
0s   - Connection established
15s  - Heartbeat #1
30s  - Heartbeat #2
45s  - Heartbeat #3
50s  - Send timeout event, close gracefully
60s  - Vercel hard timeout (avoided)

Browser behavior:
- Receives timeout event
- Connection closes
- EventSource auto-reconnects (sends Last-Event-ID)
- Server resumes from last event ID
```

## Message Broadcasting (Stateless Pattern)

Since serverless functions can't share memory, use external storage:

### Option 1: Database Polling
```python
async def event_stream(user_id: int, last_event_id: str = None):
    while True:
        # Query new notifications since last_event_id
        notifications = await db.query(
            Notification
        ).filter(
            Notification.user_id == user_id,
            Notification.id > last_event_id
        ).all()
        
        for notif in notifications:
            yield format_sse(notif.dict(), event_id=notif.id)
            last_event_id = notif.id
        
        await asyncio.sleep(1)
```

### Option 2: Redis Pub/Sub (Better for high volume)
```python
async def event_stream(user_id: int):
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"user:{user_id}:notifications")
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            yield f"data: {message['data']}\n\n"
```

## Migration Checklist

- [x] Create `app/core/sse.py` with SSEManager
- [x] Implement stateless event streaming
- [x] Add heartbeat mechanism (15s interval)
- [x] Add 50s timeout safety (before Vercel 60s limit)
- [x] Create `docs/SSE_MIGRATION.md`
- [ ] Update `/api/v1/realtime/notifications` endpoint (T12)
- [ ] Update frontend to use EventSource (separate task)
- [ ] Test reconnection behavior
- [ ] Monitor Vercel function duration (must be <60s)
- [ ] Implement Redis/DB message queue for broadcasting

## API Endpoint Example

```python
# app/api/endpoints/realtime.py
from fastapi import APIRouter, Depends, Query
from app.core.sse import create_sse_stream
from app.core.security import get_current_user_from_token
from app.models.user import User

router = APIRouter()

@router.get("/stream")
async def stream_notifications(
    token: str = Query(..., description="JWT access token"),
    last_event_id: str = Query(None, alias="Last-Event-ID"),
):
    """
    SSE endpoint for real-time notifications.
    
    Browser auto-reconnects and sends Last-Event-ID header.
    Token passed via query param (EventSource limitation).
    """
    user = await get_current_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return create_sse_stream(user.id, last_event_id)
```

## Comparison: When to Use What

| Use Case | Recommendation |
|----------|----------------|
| Server → Client notifications | ✅ SSE |
| Bidirectional chat | ❌ SSE (use external service) |
| Real-time dashboard updates | ✅ SSE |
| File upload progress | ❌ SSE (use polling) |
| Serverless deployment | ✅ SSE |
| Traditional server | Either (WebSocket slightly better) |

## External Alternatives (For >60s Connections)

If you need persistent connections beyond 60s:

1. **Pusher** - Managed WebSocket service
2. **Ably** - Real-time messaging platform
3. **Firebase Realtime Database** - Google's real-time sync
4. **Supabase Realtime** - PostgreSQL-based real-time

These services maintain long-lived connections and push events to your serverless functions.
