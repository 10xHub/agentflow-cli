"""Checkpointer API schemas."""

from typing import Any

from pyagenity.state import AgentState
from pyagenity.utils import Message
from pydantic import BaseModel, Field


########################
#### State Related #####
########################
class ConfigInputSchema(BaseModel):
    """Schema for state data."""

    config: dict[str, Any] = Field(..., description="Configuration for the state")


class StateResponseSchema(BaseModel):
    """Schema for state response."""

    state: AgentState | None = Field(None, description="State data")


class PutStateSchema(BaseModel):
    """Schema for putting state."""

    config: dict[str, Any] = Field(..., description="Configuration for the state")
    state: AgentState = Field(..., description="State data")


class PutMessagesSchema(BaseModel):
    """Schema for putting messages."""

    config: dict[str, Any] = Field(..., description="Configuration for the messages")
    messages: list[Message] = Field(..., description="List of messages to store")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")


class GetMessageSchema(BaseModel):
    """Schema for getting a single message."""

    config: dict[str, Any] = Field(..., description="Configuration for getting message")
    message_id: str = Field(..., description="Message ID to retrieve")


class ListMessagesSchema(BaseModel):
    """Schema for listing messages."""

    config: dict[str, Any] = Field(..., description="Configuration for listing messages")
    search: str | None = Field(None, description="Search query")
    offset: int | None = Field(None, description="Number of messages to skip")
    limit: int | None = Field(None, description="Maximum number of messages to return")


class DeleteMessageSchema(BaseModel):
    """Schema for deleting a message."""

    config: dict[str, Any] = Field(..., description="Configuration for deleting message")
    message_id: str = Field(..., description="Message ID to delete")


class PutThreadSchema(BaseModel):
    """Schema for putting thread info."""

    config: dict[str, Any] = Field(..., description="Configuration for the thread")
    thread_info: dict[str, Any] = Field(..., description="Thread information to store")


class GetThreadSchema(BaseModel):
    """Schema for getting a thread."""

    config: dict[str, Any] = Field(..., description="Configuration for getting thread")
    thread_id: str = Field(..., description="Thread ID to retrieve")


class ListThreadsSchema(BaseModel):
    """Schema for listing threads."""

    config: dict[str, Any] = Field(..., description="Configuration for the thread")
    search: str | None = Field(None, description="Search query")
    offset: int | None = Field(None, description="Number of threads to skip")
    limit: int | None = Field(None, description="Maximum number of threads to return")


class DeleteThreadSchema(BaseModel):
    """Schema for deleting a thread."""

    config: dict[str, Any] = Field(..., description="Configuration for deleting thread")
    thread_id: str = Field(..., description="Thread ID to delete")


class CleanupSchema(BaseModel):
    """Schema for cleanup operation."""

    config: dict[str, Any] = Field(..., description="Configuration for cleanup")


class SyncStateSchema(BaseModel):
    """Schema for sync state operation."""

    config: dict[str, Any] = Field(..., description="Configuration for sync")
    state: dict[str, Any] = Field(..., description="State data to sync")


class GetSyncStateSchema(BaseModel):
    """Schema for getting sync state."""

    config: dict[str, Any] = Field(..., description="Configuration for getting sync state")


# Response schemas
class ResponseSchema(BaseModel):
    """Base response schema for checkpointer operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Any | None = Field(None, description="Response data")


class MessageResponseSchema(BaseModel):
    """Response schema for message operations."""

    message: Message | None = Field(None, description="Message data")


class MessagesListResponseSchema(BaseModel):
    """Response schema for message list operations."""

    messages: list[Message] | None = Field(None, description="List of messages")


class ThreadResponseSchema(BaseModel):
    """Response schema for thread operations."""

    thread: dict[str, Any] | None = Field(None, description="Thread data")


class ThreadsListResponseSchema(BaseModel):
    """Response schema for thread list operations."""

    threads: list[dict[str, Any]] | None = Field(None, description="List of threads")
