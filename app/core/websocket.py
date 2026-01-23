from typing import List
from fastapi import WebSocket
from app.core.logging import logger

class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept connection and add to list."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection from list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send message to all active connections."""
        if not self.active_connections:
            return

        logger.info(f"Broadcasting message to {len(self.active_connections)} clients: {message}")
        
        # Iterate over a copy to avoid modification issues during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                self.disconnect(connection)

# Singleton instance
manager = ConnectionManager()
