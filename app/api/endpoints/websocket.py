from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from app.core.websocket import manager
from app.core.security import get_current_user_from_token
from app.core.logging import logger

router = APIRouter()

@router.websocket("/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket Endpoint for real-time notifications.
    Clients must connect with ?token={access_token}
    """
    try:
        # Validate Token
        user = await get_current_user_from_token(token)
        if not user:
            logger.warning("WebSocket authentication failed: Invalid token")
            await websocket.accept()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect
        await manager.connect(websocket)
        
        try:
            while True:
                # Keep connection alive and listen for messages (optional)
                # For now, we only push notifications (server -> client)
                data = await websocket.receive_text()
                # logger.info(f"Received message from client: {data}")
                
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
