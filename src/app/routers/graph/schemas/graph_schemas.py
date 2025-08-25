from typing import Any, Optional

from pyagenity.state import AgentState
from pyagenity.utils import Message, ResponseGranularity
from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    message_id: int | None = Field(None, description="Unique identifier for the message")
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
    initial_state: dict[str, Any] | None = Field(
        default=None,
        description="Initial state for the graph execution",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Optional configuration for graph execution",
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

    messages: list[Message] = Field(
        ...,
        description="Final processed messages from the graph",
    )
    state: AgentState | None = Field(
        default=None,
        description="State information from the graph execution",
    )
    context: list[Message] | None = Field(
        default=None,
        description="Context information from the graph execution",
    )
    summary: str | None = Field(
        default=None,
        description="Summary information from the graph execution",
    )
    meta: dict[str, Any] | None = Field(
        default=None,
        description="Meta information from the graph execution",
    )


class GraphStreamChunkSchema(BaseModel):
    """
    Schema for individual stream chunks from graph execution.
    """

    data: dict[str, Any] = Field(..., description="Chunk data")
    metadata: dict[str, Any] | None = Field(default=None, description="Chunk metadata")
