# """
# Agent-to-UI (A2UI) WebSocket API Endpoints

# Provides real-time communication from agents to the UI using WebSockets.
# """

# import asyncio
# import json
# import logging
# from datetime import datetime, timezone
# from typing import Any

# from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
# from pydantic import BaseModel

# logger = logging.getLogger(__name__)

# router = APIRouter(tags=["A2UI"])


# class ConnectionManager:
#     """Manages WebSocket connections for A2UI."""

#     def __init__(self):
#         self.active_connections: dict[str, list[WebSocket]] = {}

#     async def connect(self, websocket: WebSocket, agent_id: str):
#         """Connect a client to an agent's updates."""
#         await websocket.accept()

#         if agent_id not in self.active_connections:
#             self.active_connections[agent_id] = []

#         self.active_connections[agent_id].append(websocket)
#         logger.info(
#             f"Client connected to agent {agent_id}. "
#             f"Total connections: {len(self.active_connections[agent_id])}"
#         )

#     def disconnect(self, websocket: WebSocket, agent_id: str):
#         """Disconnect a client from an agent's updates."""
#         if agent_id in self.active_connections:
#             if websocket in self.active_connections[agent_id]:
#                 self.active_connections[agent_id].remove(websocket)

#                 if not self.active_connections[agent_id]:
#                     del self.active_connections[agent_id]

#                 logger.info(
#                     f"Client disconnected from agent {agent_id}. "
#                     f"Remaining connections: "
#                     f"{len(self.active_connections.get(agent_id, []))}"
#                 )

#     async def send_to_agent_subscribers(
#         self,
#         agent_id: str,
#         message: dict[str, Any],
#     ):
#         """Send message to all subscribers of an agent."""
#         if agent_id not in self.active_connections:
#             return

#         # Send to all connected clients
#         disconnected = []
#         for connection in self.active_connections[agent_id]:
#             try:
#                 await connection.send_json(message)
#             except Exception as e:
#                 logger.error(f"Error sending message: {e}")
#                 disconnected.append(connection)

#         # Clean up disconnected clients
#         for connection in disconnected:
#             self.disconnect(connection, agent_id)

#     async def broadcast(self, message: dict[str, Any]):
#         """Broadcast message to all connected clients."""
#         for agent_id in list(self.active_connections.keys()):
#             await self.send_to_agent_subscribers(agent_id, message)

#     def get_connection_count(self, agent_id: str | None = None) -> int:
#         """Get number of active connections."""
#         if agent_id:
#             return len(self.active_connections.get(agent_id, []))
#         return sum(len(conns) for conns in self.active_connections.values())


# # Global connection manager
# manager = ConnectionManager()


# class A2UIMessage(BaseModel):
#     """A2UI message structure."""

#     message_type: str
#     agent_id: str
#     timestamp: str
#     data: dict[str, Any]


# @router.websocket("/ws/agents/{agent_id}")
# async def websocket_agent_updates(
#     websocket: WebSocket,
#     agent_id: str,
#     token: str | None = Query(None),
# ):
#     """
#     WebSocket endpoint for real-time agent updates.

#     Clients connect to this endpoint to receive real-time updates from a specific agent.
#     Use '*' as agent_id to receive updates from all agents.
#     """
#     # TODO: Implement authentication using token
#     # For now, accept all connections

#     try:
#         await manager.connect(websocket, agent_id)

#         # Send welcome message
#         welcome_message = A2UIMessage(
#             message_type="CONNECTED",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data={"message": f"Connected to agent {agent_id} updates"},
#         )
#         await websocket.send_json(welcome_message.model_dump())

#         # Keep connection alive and handle incoming messages
#         while True:
#             try:
#                 # Wait for messages from client (e.g., ping, subscription changes)
#                 data = await websocket.receive_text()

#                 # Handle client messages if needed
#                 try:
#                     client_msg = json.loads(data)
#                     if client_msg.get("type") == "ping":
#                         await websocket.send_json({"type": "pong"})
#                 except json.JSONDecodeError:
#                     logger.warning(f"Invalid JSON received: {data}")

#             except WebSocketDisconnect:
#                 break
#             except Exception as e:
#                 logger.error(f"Error in WebSocket loop: {e}")
#                 break

#     except Exception as e:
#         logger.error(f"WebSocket error: {e}")
#     finally:
#         manager.disconnect(websocket, agent_id)


# @router.post("/api/v1/a2ui/send")
# async def send_agent_update(
#     agent_id: str,
#     message_type: str,
#     data: dict[str, Any],
# ):
#     """
#     Send an update from an agent to all subscribed UI clients.

#     This endpoint is called by agents to push updates to connected UIs.
#     """
#     try:
#         message = A2UIMessage(
#             message_type=message_type,
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         )

#         await manager.send_to_agent_subscribers(agent_id, message.model_dump())

#         # Also send to wildcard subscribers (agent_id = "*")
#         if agent_id != "*":
#             await manager.send_to_agent_subscribers("*", message.model_dump())

#         return {
#             "success": True,
#             "message": "Update sent to subscribers",
#             "subscriber_count": manager.get_connection_count(agent_id),
#         }

#     except Exception as e:
#         logger.error(f"Error sending agent update: {e}")
#         return {"success": False, "error": str(e)}


# @router.post("/api/v1/a2ui/broadcast")
# async def broadcast_update(
#     message_type: str,
#     data: dict[str, Any],
#     sender_id: str = "system",
# ):
#     """
#     Broadcast an update to all connected UI clients.

#     This is useful for system-wide notifications.
#     """
#     try:
#         message = A2UIMessage(
#             message_type=message_type,
#             agent_id=sender_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         )

#         await manager.broadcast(message.model_dump())

#         return {
#             "success": True,
#             "message": "Broadcast sent to all subscribers",
#             "total_connections": manager.get_connection_count(),
#         }

#     except Exception as e:
#         logger.error(f"Error broadcasting update: {e}")
#         return {"success": False, "error": str(e)}


# @router.get("/api/v1/a2ui/connections")
# async def get_connection_stats(agent_id: str | None = None):
#     """Get statistics about active WebSocket connections."""
#     if agent_id:
#         count = manager.get_connection_count(agent_id)
#         return {
#             "agent_id": agent_id,
#             "connection_count": count,
#         }
#     else:
#         return {
#             "total_connections": manager.get_connection_count(),
#             "agents": {
#                 aid: len(conns)
#                 for aid, conns in manager.active_connections.items()
#             },
#         }


# # Helper function for agents to send updates
# async def send_agent_status_update(
#     agent_id: str,
#     status: str,
#     message: str | None = None,
#     metadata: dict[str, Any] | None = None,
# ):
#     """Helper to send agent status update."""
#     data = {"status": status}
#     if message:
#         data["message"] = message
#     if metadata:
#         data["metadata"] = metadata

#     await manager.send_to_agent_subscribers(
#         agent_id,
#         A2UIMessage(
#             message_type="AGENT_STATUS",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         ).model_dump(),
#     )


# async def send_agent_message(
#     agent_id: str,
#     content: str,
#     role: str,
#     message_id: str | None = None,
#     metadata: dict[str, Any] | None = None,
# ):
#     """Helper to send agent message update."""
#     data = {"content": content, "role": role}
#     if message_id:
#         data["message_id"] = message_id
#     if metadata:
#         data["metadata"] = metadata

#     await manager.send_to_agent_subscribers(
#         agent_id,
#         A2UIMessage(
#             message_type="AGENT_MESSAGE",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         ).model_dump(),
#     )


# async def send_agent_thinking(
#     agent_id: str,
#     thinking: str,
#     step: str | None = None,
#     metadata: dict[str, Any] | None = None,
# ):
#     """Helper to send agent thinking update."""
#     data = {"thinking": thinking}
#     if step:
#         data["step"] = step
#     if metadata:
#         data["metadata"] = metadata

#     await manager.send_to_agent_subscribers(
#         agent_id,
#         A2UIMessage(
#             message_type="AGENT_THINKING",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         ).model_dump(),
#     )


# async def send_agent_error(
#     agent_id: str,
#     error: str,
#     error_code: str | None = None,
#     metadata: dict[str, Any] | None = None,
# ):
#     """Helper to send agent error update."""
#     data = {"error": error}
#     if error_code:
#         data["error_code"] = error_code
#     if metadata:
#         data["metadata"] = metadata

#     await manager.send_to_agent_subscribers(
#         agent_id,
#         A2UIMessage(
#             message_type="AGENT_ERROR",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         ).model_dump(),
#     )


# async def send_agent_complete(
#     agent_id: str,
#     result: Any,
#     duration: float | None = None,
#     metadata: dict[str, Any] | None = None,
# ):
#     """Helper to send agent completion update."""
#     data = {"result": result}
#     if duration:
#         data["duration"] = duration
#     if metadata:
#         data["metadata"] = metadata

#     await manager.send_to_agent_subscribers(
#         agent_id,
#         A2UIMessage(
#             message_type="AGENT_COMPLETE",
#             agent_id=agent_id,
#             timestamp=datetime.now(timezone.utc).isoformat(),
#             data=data,
#         ).model_dump(),
#     )

