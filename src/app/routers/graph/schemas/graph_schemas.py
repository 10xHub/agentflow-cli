from typing import Any, Optional

from pyagenity.utils import ResponseGranularity
from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    message_id: Optional[int] = Field(None, description="Unique identifier for the message")
    role: str = Field(
        default="user", description="Role of the message sender (user, assistant, etc.)"
    )
    content: str = Field(..., description="Content of the message")


class GraphInputSchema(BaseModel):
    """
    Schema for graph input including messages and configuration.
    """

    messages: list[MessageSchema] = Field(
        ..., description="List of messages to process through the graph"
    )
    initial_state: Optional[dict[str, Any]] = Field(
        default=None,
        description="Initial state for the graph execution",
    )
    config: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional configuration for graph execution",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for conversation context",
    )
    recursion_limit: int = Field(
        default=25,
        description="Maximum recursion limit for graph execution",
    )
    response_granularity: ResponseGranularity = Field(
        default=ResponseGranularity.LOW,
        description="Granularity of the response (full, partial, low)",
    )
    include_raw: bool = Field(
        default=False,
        description="Whether to include raw response data",
    )


class GraphInvokeOutputSchema(BaseModel):
    """
    Schema for graph invoke output.
    """

    messages: list[dict[str, Any]] = Field(
        ..., description="Final processed messages from the graph"
    )
    state: Optional[dict[str, Any]] = Field(
        default=None,
        description="State information from the graph execution",
    )
    context: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Context information from the graph execution",
    )
    summary: Optional[str] = Field(
        default=None,
        description="Summary information from the graph execution",
    )
    meta: Optional[dict[str, Any]] = Field(
        default=None,
        description="Meta information from the graph execution",
    )


class GraphStreamChunkSchema(BaseModel):
    """
    Schema for individual stream chunks from graph execution.
    """

    data: dict[str, Any] = Field(..., description="Chunk data")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Chunk metadata")
