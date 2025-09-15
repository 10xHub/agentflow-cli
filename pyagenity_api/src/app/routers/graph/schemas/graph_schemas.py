from typing import Any

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
    state: dict[str, Any] | None = Field(
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


class NodeSchema(BaseModel):
    """Schema for individual graph nodes."""

    id: str = Field(..., description="Unique identifier for the node")
    name: str = Field(..., description="Name of the node")


class EdgeSchema(BaseModel):
    """Schema for individual graph edges."""

    id: str = Field(..., description="Unique identifier for the edge")
    source: str = Field(..., description="Source node identifier")
    target: str = Field(..., description="Target node identifier")


class GraphInfoSchema(BaseModel):
    """Schema for graph metadata and configuration."""

    node_count: int = Field(..., description="Number of nodes in the graph")
    edge_count: int = Field(..., description="Number of edges in the graph")
    checkpointer: bool = Field(..., description="Whether checkpointer is enabled")
    checkpointer_type: str | None = Field(None, description="Type of checkpointer if enabled")
    publisher: bool = Field(..., description="Whether publisher is enabled")
    store: bool = Field(..., description="Whether store is enabled")
    interrupt_before: list[str] | None = Field(None, description="Nodes to interrupt before")
    interrupt_after: list[str] | None = Field(None, description="Nodes to interrupt after")


class GraphSchema(BaseModel):
    """Schema for the complete graph structure."""

    info: GraphInfoSchema = Field(..., description="Graph metadata and configuration")
    nodes: list[NodeSchema] = Field(..., description="List of nodes in the graph")
    edges: list[EdgeSchema] = Field(..., description="List of edges in the graph")
