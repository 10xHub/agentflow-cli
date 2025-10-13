"""Store router module."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.auth_backend import verify_current_user
from agentflow_cli.src.app.utils.response_helper import success_response
from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses

from .schemas.store_schemas import (
    DeleteMemorySchema,
    ForgetMemorySchema,
    MemoryCreateResponseSchema,
    MemoryItemResponseSchema,
    MemoryListResponseSchema,
    MemoryOperationResponseSchema,
    MemorySearchResponseSchema,
    SearchMemorySchema,
    StoreMemorySchema,
    UpdateMemorySchema,
)
from .services.store_service import StoreService


router = APIRouter(tags=["store"])


def _parse_optional_json(param_name: str, raw_value: str | None) -> dict[str, Any] | None:
    """Parse optional JSON query parameters into dictionaries."""

    if raw_value is None:
        return None

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON supplied for '{param_name}'.",
        ) from exc

    if parsed is None:
        return None

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameter '{param_name}' must decode to an object (dict).",
        )

    return parsed


@router.post(
    "/v1/store/memories",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryCreateResponseSchema),
    summary="Store a memory",
    description="Persist a memory payload using the configured store backend.",
)
async def create_memory(
    request: Request,
    payload: StoreMemorySchema,
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Store a memory item using the configured store."""

    logger.debug("User info: %s", user)
    result = await service.store_memory(payload, user)
    return success_response(result, request, message="Memory stored successfully")


@router.post(
    "/v1/store/search",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemorySearchResponseSchema),
    summary="Search memories",
    description="Search memories stored in the backend based on semantic similarity and filters.",
)
async def search_memories(
    request: Request,
    payload: SearchMemorySchema,
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Search stored memories."""

    logger.debug("User info: %s", user)
    result = await service.search_memories(payload, user)
    return success_response(result, request)


@router.get(
    "/v1/store/memories/{memory_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryItemResponseSchema),
    summary="Get a memory",
    description="Retrieve a memory by its identifier from the configured store backend.",
)
async def get_memory(
    request: Request,
    memory_id: str,
    config: str | None = Query(
        default=None,
        description="JSON-encoded configuration overrides forwarded to the store backend.",
    ),
    options: str | None = Query(
        default=None,
        description="JSON-encoded options forwarded to the store backend.",
    ),
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Get a memory by ID."""

    logger.debug("User info: %s", user)
    cfg = _parse_optional_json("config", config) or {}
    opts = _parse_optional_json("options", options)
    result = await service.get_memory(memory_id, cfg, user, options=opts)
    return success_response(result, request)


@router.get(
    "/v1/store/memories",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryListResponseSchema),
    summary="List memories",
    description="List memories from the configured store backend.",
)
async def list_memories(
    request: Request,
    limit: int = Query(100, gt=0, description="Maximum number of memories to return."),
    config: str | None = Query(
        default=None,
        description="JSON-encoded configuration overrides forwarded to the store backend.",
    ),
    options: str | None = Query(
        default=None,
        description="JSON-encoded options forwarded to the store backend.",
    ),
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """List stored memories."""

    logger.debug("User info: %s", user)
    cfg = _parse_optional_json("config", config) or {}
    opts = _parse_optional_json("options", options)
    result = await service.list_memories(cfg, user, limit=limit, options=opts)
    return success_response(result, request)


@router.put(
    "/v1/store/memories/{memory_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryOperationResponseSchema),
    summary="Update a memory",
    description="Update the content or metadata of a stored memory.",
)
async def update_memory(
    request: Request,
    memory_id: str,
    payload: UpdateMemorySchema,
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Update a stored memory."""

    logger.debug("User info: %s", user)
    result = await service.update_memory(memory_id, payload, user)
    return success_response(result, request, message="Memory updated successfully")


@router.delete(
    "/v1/store/memories/{memory_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryOperationResponseSchema),
    summary="Delete a memory",
    description="Delete a stored memory by its identifier.",
)
async def delete_memory(
    request: Request,
    memory_id: str,
    payload: DeleteMemorySchema | None = Body(
        default=None,
        description="Optional configuration overrides forwarded to the store backend.",
    ),
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Delete a stored memory."""

    logger.debug("User info: %s", user)
    config_payload = payload.config if payload else {}
    options_payload = payload.options if payload else None
    result = await service.delete_memory(memory_id, config_payload, user, options=options_payload)
    return success_response(result, request, message="Memory deleted successfully")


@router.post(
    "/v1/store/memories/forget",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MemoryOperationResponseSchema),
    summary="Forget memories",
    description="Forget memories matching the provided filters from the store backend.",
)
async def forget_memory(
    request: Request,
    payload: ForgetMemorySchema,
    service: StoreService = InjectAPI(StoreService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Forget memories based on filters."""

    logger.debug("User info: %s", user)
    result = await service.forget_memory(payload, user)
    return success_response(result, request, message="Memories removed successfully")
