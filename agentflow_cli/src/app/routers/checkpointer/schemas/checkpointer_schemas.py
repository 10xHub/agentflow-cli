"""Checkpointer API schemas."""

from typing import Any

from agentflow.state import Message
from pydantic import BaseModel, Field


class ConfigSchema(BaseModel):
    """Schema for state data."""

    config: dict[str, Any] | None = Field(
        default_factory=dict, description="Configuration for the state"
    )


class StateResponseSchema(BaseModel):
    """Schema for state response."""

    state: dict[str, Any] | None = Field(None, description="State data")


class StateSchema(ConfigSchema):
    """Schema for putting state."""

    state: dict[str, Any] = Field(..., description="State data")


class PutMessagesSchema(ConfigSchema):
    """Schema for putting messages."""

    messages: list[Message] = Field(..., description="List of messages to store")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")


class GetMessageSchema(ConfigSchema):
    """Schema for getting a single message."""

    message_id: str = Field(..., description="Message ID to retrieve")


class ListMessagesSchema(ConfigSchema):
    """Schema for listing messages."""

    search: str | None = Field(None, description="Search query")
    offset: int | None = Field(None, description="Number of messages to skip")
    limit: int | None = Field(None, description="Maximum number of messages to return")


class DeleteMessageSchema(ConfigSchema):
    """Schema for deleting a message."""

    message_id: str = Field(..., description="Message ID to delete")


class PutThreadSchema(ConfigSchema):
    """Schema for putting thread info."""

    thread_info: dict[str, Any] = Field(..., description="Thread information to store")


class GetThreadSchema(ConfigSchema):
    """Schema for getting a thread."""

    thread_id: str = Field(..., description="Thread ID to retrieve")


class ListThreadsSchema(ConfigSchema):
    """Schema for listing threads."""

    search: str | None = Field(None, description="Search query")
    offset: int | None = Field(None, description="Number of threads to skip")
    limit: int | None = Field(None, description="Maximum number of threads to return")


class DeleteThreadSchema(ConfigSchema):
    """Schema for deleting a thread."""

    thread_id: str = Field(..., description="Thread ID to delete")


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
