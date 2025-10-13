"""Store API schemas."""

from __future__ import annotations

from typing import Any

from agentflow.state import Message
from agentflow.store.store_schema import (
    DistanceMetric,
    MemoryRecord,
    MemorySearchResult,
    MemoryType,
    RetrievalStrategy,
)
from pydantic import BaseModel, Field


class BaseConfigSchema(BaseModel):
    """Base schema containing configuration overrides and store options."""

    config: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Configuration values forwarded to the store backend.",
    )
    options: dict[str, Any] | None = Field(
        default=None,
        description="Extra keyword arguments to forward to the store backend.",
    )


class StoreMemorySchema(BaseConfigSchema):
    """Schema for storing a memory item."""

    content: str | Message = Field(..., description="Memory content or structured message.")
    memory_type: MemoryType = Field(
        default=MemoryType.EPISODIC,
        description="Memory classification used by the backend store.",
    )
    category: str = Field(default="general", description="Category label for the memory.")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary metadata associated with the memory.",
    )


class SearchMemorySchema(BaseConfigSchema):
    """Schema for searching memories."""

    query: str = Field(..., description="Textual query used for memory retrieval.")
    memory_type: MemoryType | None = Field(
        default=None,
        description="Optional memory type filter.",
    )
    category: str | None = Field(
        default=None,
        description="Optional category filter.",
    )
    limit: int = Field(default=10, gt=0, description="Maximum number of results to return.")
    score_threshold: float | None = Field(
        default=None,
        description="Minimum similarity score required for results.",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Additional store-specific filters.",
    )
    retrieval_strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.SIMILARITY,
        description="Retrieval strategy used by the backend store.",
    )
    distance_metric: DistanceMetric = Field(
        default=DistanceMetric.COSINE,
        description="Distance metric applied during similarity search.",
    )
    max_tokens: int = Field(
        default=4000,
        gt=0,
        description="Maximum tokens used for truncation in similarity search.",
    )


class UpdateMemorySchema(BaseConfigSchema):
    """Schema for updating a memory."""

    content: str | Message = Field(..., description="Updated memory content or message.")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Updated metadata for the memory.",
    )


class DeleteMemorySchema(BaseConfigSchema):
    """Schema for deleting a memory."""


class ForgetMemorySchema(BaseConfigSchema):
    """Schema for forgetting memories based on filters."""

    memory_type: MemoryType | None = Field(
        default=None,
        description="Optional memory type to target for deletion.",
    )
    category: str | None = Field(
        default=None,
        description="Optional category to target for deletion.",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Additional filters to control which memories are forgotten.",
    )


class MemoryCreateResponseSchema(BaseModel):
    """Response schema for create memory operations."""

    memory_id: str = Field(..., description="Identifier of the stored memory.")


class MemoryItemResponseSchema(BaseModel):
    """Response schema for single memory retrieval."""

    memory: MemorySearchResult | None = Field(
        default=None,
        description="Memory retrieved from the store, if available.",
    )


class MemoryListResponseSchema(BaseModel):
    """Response schema for listing memories."""

    memories: list[MemorySearchResult] = Field(
        default_factory=list,
        description="Collection of memories returned from the store.",
    )


class MemorySearchResponseSchema(BaseModel):
    """Response schema for search operations."""

    results: list[MemorySearchResult] = Field(
        default_factory=list,
        description="Search results ranked by relevance.",
    )


class MemoryOperationResponseSchema(BaseModel):
    """Generic response schema for mutation operations."""

    success: bool = Field(..., description="Whether the store operation succeeded.")
    data: Any | None = Field(default=None, description="Optional payload returned by the store.")


__all__ = [
    "BaseConfigSchema",
    "DeleteMemorySchema",
    "DistanceMetric",
    "ForgetMemorySchema",
    "MemoryCreateResponseSchema",
    "MemoryItemResponseSchema",
    "MemoryListResponseSchema",
    "MemoryOperationResponseSchema",
    "MemoryRecord",
    "MemorySearchResponseSchema",
    "MemorySearchResult",
    "MemoryType",
    "RetrievalStrategy",
    "SearchMemorySchema",
    "StoreMemorySchema",
    "UpdateMemorySchema",
]
