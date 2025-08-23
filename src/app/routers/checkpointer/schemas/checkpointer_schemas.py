"""Checkpointer API schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class StateSchema(BaseModel):
    """Schema for state data."""

    config: dict[str, Any] = Field(..., description="Configuration for the state")
    state: dict[str, Any] = Field(..., description="State data")


class PutMessagesSchema(BaseModel):
    """Schema for putting messages."""

    config: dict[str, Any] = Field(..., description="Configuration for the messages")
    messages: list[dict[str, Any]] = Field(..., description="List of message data to store")
    metadata: Optional[dict[str, Any]] = Field(None, description="Optional metadata")


class GetMessageSchema(BaseModel):
    """Schema for getting a single message."""

    config: dict[str, Any] = Field(..., description="Configuration for getting message")


class ListMessagesSchema(BaseModel):
    """Schema for listing messages."""

    config: dict[str, Any] = Field(..., description="Configuration for listing messages")
    search: Optional[str] = Field(None, description="Search query")
    offset: Optional[int] = Field(None, description="Number of messages to skip")
    limit: Optional[int] = Field(None, description="Maximum number of messages to return")


class DeleteMessageSchema(BaseModel):
    """Schema for deleting a message."""

    config: dict[str, Any] = Field(..., description="Configuration for deleting message")


class PutThreadSchema(BaseModel):
    """Schema for putting thread info."""

    config: dict[str, Any] = Field(..., description="Configuration for the thread")
    thread_info: dict[str, Any] = Field(..., description="Thread information to store")


class GetThreadSchema(BaseModel):
    """Schema for getting a thread."""

    config: dict[str, Any] = Field(..., description="Configuration for getting thread")


class ListThreadsSchema(BaseModel):
    """Schema for listing threads."""

    search: Optional[str] = Field(None, description="Search query")
    offset: Optional[int] = Field(None, description="Number of threads to skip")
    limit: Optional[int] = Field(None, description="Maximum number of threads to return")


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
class CheckpointerResponseSchema(BaseModel):
    """Base response schema for checkpointer operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data")


class StateResponseSchema(CheckpointerResponseSchema):
    """Response schema for state operations."""

    state: Optional[dict[str, Any]] = Field(None, description="State data")


class MessageResponseSchema(CheckpointerResponseSchema):
    """Response schema for message operations."""

    message_data: Optional[dict[str, Any]] = Field(None, description="Message data")


class MessagesListResponseSchema(CheckpointerResponseSchema):
    """Response schema for message list operations."""

    messages: Optional[list[dict[str, Any]]] = Field(None, description="List of messages")
    total: Optional[int] = Field(None, description="Total number of messages")


class ThreadResponseSchema(CheckpointerResponseSchema):
    """Response schema for thread operations."""

    thread_data: Optional[dict[str, Any]] = Field(None, description="Thread data")


class ThreadsListResponseSchema(CheckpointerResponseSchema):
    """Response schema for thread list operations."""

    threads: Optional[list[dict[str, Any]]] = Field(None, description="List of threads")
    total: Optional[int] = Field(None, description="Total number of threads")
