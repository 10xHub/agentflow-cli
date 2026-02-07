# """
# Agent-to-Agent (A2A) Communication API Endpoints
# """

# from typing import Any

# from fastapi import APIRouter, Depends, HTTPException, Request
# from pydantic import BaseModel, Field

# from agentflow.communication import A2ACommunicationManager
# from agentflow.protocols.acp import ACPMessage

# router = APIRouter(prefix="/api/v1/agents", tags=["A2A"])

# # Global communication manager instance
# # TODO: Initialize this properly in app startup
# comm_manager: A2ACommunicationManager | None = None


# def get_comm_manager(request: Request) -> A2ACommunicationManager:
#     """Dependency to get communication manager."""
#     global comm_manager
#     if comm_manager is None:
#         # Initialize if not exists
#         comm_manager = A2ACommunicationManager()
#     return comm_manager


# class RegisterAgentRequest(BaseModel):
#     """Request to register an agent."""

#     agent_id: str = Field(..., description="Unique agent identifier")
#     agent_name: str = Field(..., description="Human-readable agent name")
#     agent_type: str = Field(default="agent", description="Type of agent")
#     capabilities: list[str] = Field(
#         default_factory=list, description="List of agent capabilities"
#     )
#     metadata: dict[str, Any] = Field(
#         default_factory=dict, description="Additional metadata"
#     )


# class SendMessageRequest(BaseModel):
#     """Request to send a message to an agent."""

#     sender_id: str = Field(..., description="Sending agent ID")
#     action: str = Field(..., description="Action to perform")
#     data: dict[str, Any] = Field(default_factory=dict, description="Message data")
#     priority: int = Field(default=5, ge=1, le=10, description="Message priority")
#     ttl: int | None = Field(None, gt=0, description="Time-to-live in seconds")
#     context: dict[str, Any] | None = Field(None, description="Message context")


# class BroadcastMessageRequest(BaseModel):
#     """Request to broadcast a message."""

#     action: str = Field(..., description="Action to broadcast")
#     data: dict[str, Any] = Field(default_factory=dict, description="Message data")
#     priority: int = Field(default=5, ge=1, le=10, description="Message priority")


# class NotificationRequest(BaseModel):
#     """Request to send a notification."""

#     sender_id: str = Field(..., description="Sending agent ID")
#     action: str = Field(..., description="Notification action")
#     data: dict[str, Any] = Field(default_factory=dict, description="Notification data")


# class UpdateStatusRequest(BaseModel):
#     """Request to update agent status."""

#     status: str = Field(..., description="New status")


# @router.post("/register")
# async def register_agent(
#     request: RegisterAgentRequest,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Register a new agent in the system."""
#     try:
#         registered = await manager.register_agent(
#             agent_id=request.agent_id,
#             agent_name=request.agent_name,
#             agent_type=request.agent_type,
#             capabilities=request.capabilities,
#             metadata=request.metadata,
#         )

#         return {
#             "success": True,
#             "message": (
#                 f"Agent '{request.agent_name}' "
#                 f"{'registered' if registered else 'updated'} successfully"
#             ),
#             "agent_id": request.agent_id,
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.delete("/{agent_id}")
# async def unregister_agent(
#     agent_id: str,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Unregister an agent from the system."""
#     try:
#         unregistered = await manager.unregister_agent(agent_id)

#         if not unregistered:
#             raise HTTPException(status_code=404, detail="Agent not found")

#         return {
#             "success": True,
#             "message": f"Agent {agent_id} unregistered successfully",
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/{recipient_id}/message")
# async def send_message(
#     recipient_id: str,
#     request: SendMessageRequest,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Send a direct message to an agent."""
#     try:
#         context_dict = request.context or {}

#         response = await manager.send_message(
#             sender_id=request.sender_id,
#             recipient_id=recipient_id,
#             action=request.action,
#             data=request.data,
#             priority=request.priority,
#             ttl=request.ttl,
#             context=context_dict,
#         )

#         if response:
#             return response.model_dump()
#         else:
#             return None

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/{sender_id}/broadcast")
# async def broadcast_message(
#     sender_id: str,
#     request: BroadcastMessageRequest,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Broadcast a message to all agents."""
#     try:
#         await manager.broadcast_message(
#             sender_id=sender_id,
#             action=request.action,
#             data=request.data,
#             priority=request.priority,
#         )

#         return {"success": True, "message": "Message broadcasted successfully"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/{recipient_id}/notification")
# async def send_notification(
#     recipient_id: str,
#     request: NotificationRequest,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Send a notification to an agent."""
#     try:
#         await manager.send_notification(
#             sender_id=request.sender_id,
#             recipient_id=recipient_id,
#             action=request.action,
#             data=request.data,
#         )

#         return {"success": True, "message": "Notification sent successfully"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("")
# async def get_active_agents(
#     agent_type: str | None = None,
#     status: str | None = None,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Get list of active agents."""
#     try:
#         agents = await manager.list_agents(agent_type=agent_type, status=status)

#         return {
#             "agents": [agent.model_dump() for agent in agents],
#             "count": len(agents),
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/{agent_id}/status")
# async def get_agent_status(
#     agent_id: str,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Get agent status."""
#     try:
#         agent = await manager.get_agent(agent_id)

#         if not agent:
#             raise HTTPException(status_code=404, detail="Agent not found")

#         return agent.model_dump()

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.put("/{agent_id}/status")
# async def update_agent_status(
#     agent_id: str,
#     request: UpdateStatusRequest,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Update agent status."""
#     try:
#         updated = await manager.update_agent_status(agent_id, request.status)

#         if not updated:
#             raise HTTPException(status_code=404, detail="Agent not found")

#         return {"success": True, "message": "Status updated successfully"}

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/{agent_id}/heartbeat")
# async def send_heartbeat(
#     agent_id: str,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Send heartbeat for an agent."""
#     try:
#         await manager.send_heartbeat(agent_id)

#         return {"success": True, "message": "Heartbeat received"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/capability/{capability}")
# async def find_agents_by_capability(
#     capability: str,
#     manager: A2ACommunicationManager = Depends(get_comm_manager),
# ):
#     """Find agents with a specific capability."""
#     try:
#         agents = await manager.find_agents_by_capability(capability)

#         return {
#             "agents": [agent.model_dump() for agent in agents],
#             "count": len(agents),
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # TODO: Add endpoint for message history
# @router.get("/{agent_id}/messages")
# async def get_agent_messages(
#     agent_id: str,
#     limit: int = 50,
#     offset: int = 0,
#     message_type: str | None = None,
# ):
#     """Get agent message history (placeholder)."""
#     # This would require message persistence
#     return {
#         "messages": [],
#         "count": 0,
#         "note": "Message history requires persistence layer implementation",
#     }

