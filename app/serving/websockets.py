from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import logging
from app.events.schema import Event
from app.events import get_event_bus


logger = logging.getLogger(__name__)


router = APIRouter(tags=["websockets"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast_event(self, event: Event):
        if not self.active_connections:
            return

        payload = event.model_dump_json()
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


manager = ConnectionManager()


# Background task to bridge EventBus and WebSockets
async def bridge_events_to_websockets(event: Event):
    await manager.broadcast_event(event)


@router.on_event("startup")
async def startup_event_bridge():
    """Hook the ConnectionManager into the EventBus"""
    try:
        bus = get_event_bus()
        bus.subscribe("*", bridge_events_to_websockets)
        logger.info("WebSocket bridge subscribed to EventBus.")
    except Exception as e:
        logger.error("Failed to subscribe WebSocket bridge to EventBus: %s", e)


@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect clients to send messages, just keep the connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(websocket)
