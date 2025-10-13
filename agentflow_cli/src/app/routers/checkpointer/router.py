"""Checkpointer router module."""

from typing import Any

from agentflow.state import Message
from fastapi import APIRouter, Depends, Request, status
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.auth_backend import verify_current_user
from agentflow_cli.src.app.utils.response_helper import success_response
from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses

from .schemas.checkpointer_schemas import (
    ConfigSchema,
    MessagesListResponseSchema,
    PutMessagesSchema,
    ResponseSchema,
    StateResponseSchema,
    StateSchema,
    ThreadResponseSchema,
    ThreadsListResponseSchema,
)
from .services.checkpointer_service import CheckpointerService


router = APIRouter(tags=["checkpointer"])


@router.get(
    "/v1/threads/{thread_id}/state",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(StateResponseSchema),
    summary="Get state from checkpointer",
    description="Retrieve state data from the checkpointer using configuration.",
)
async def get_state(
    request: Request,
    thread_id: int | str,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Get state from checkpointer.

    Args:
        request: State schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        State response with state data or error
    """
    logger.debug(f"User info: {user}")

    config = {"thread_id": thread_id}

    result = await service.get_state(
        config,
        user,
    )

    return success_response(
        result,
        request,
    )


@router.put(
    "/v1/threads/{thread_id}/state",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(StateResponseSchema),
    summary="Put state to checkpointer",
    description="Store state data in the checkpointer using configuration.",
)
async def put_state(
    request: Request,
    thread_id: str | int,
    payload: StateSchema,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Put state to checkpointer.

    Args:
        request: Request object
        payload: Put state schema with configuration and state data
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Success response or error
    """
    logger.debug(f"User info: {user}")
    config = {"thread_id": thread_id}
    if payload.config:
        config.update(payload.config)

    # State is provided as dict; service will handle merging/reconstruction
    res = await service.put_state(
        config,
        user,
        payload.state,
    )

    return success_response(
        res,
        request,
    )


@router.delete(
    "/v1/threads/{thread_id}/state",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ResponseSchema),
    summary="Clear state from checkpointer",
    description="Clear state data from the checkpointer using configuration.",
)
async def clear_state(
    request: Request,
    thread_id: int | str,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Clear state from checkpointer.

    Args:
        request: Request object
        payload: Clear state schema with configuration
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Success response or error
    """
    logger.debug(f"User info: {user}")
    config = {"thread_id": thread_id}

    res = await service.clear_state(
        config,
        user,
    )

    return success_response(
        res,
        request,
    )


# Now Handle Messages


@router.post(
    "/v1/threads/{thread_id}/messages",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ResponseSchema),
    summary="Put messages to checkpointer",
    description="Store messages in the checkpointer using configuration.",
)
async def put_messages(
    request: Request,
    thread_id: str | int,
    payload: PutMessagesSchema,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Put messages to checkpointer.

    Args:
        request: Request object
        payload: Put messages schema with configuration and messages
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Success response or error
    """
    logger.debug(f"User info: {user}")

    # Convert message dicts to Message objects if needed
    config = {"thread_id": thread_id}
    if payload.config:
        config.update(payload.config)

    res = await service.put_messages(
        config,
        user,
        payload.messages,
        payload.metadata,
    )

    return success_response(
        res,
        request,
    )


@router.get(
    "/v1/threads/{thread_id}/messages/{message_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(Message),
    summary="Get message from checkpointer",
    description=(
        "Retrieve a specific message from the checkpointer using configuration and message ID."
    ),
)
async def get_message(
    request: Request,
    thread_id: str | int,
    message_id: str | int,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Get message from checkpointer.

    Args:
        request: Request object
        payload: Get message schema with configuration and message ID
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Message response with message data or error
    """
    logger.debug(f"User info: {user}")
    config = {"thread_id": thread_id}

    result = await service.get_message(
        config,
        user,
        message_id,
    )

    return success_response(
        result,
        request,
    )


@router.get(
    "/v1/threads/{thread_id}/messages",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(MessagesListResponseSchema),
    summary="List messages from checkpointer",
    description="Retrieve a list of messages from the checkpointer using configuration "
    "and optional filters.",
)
async def list_messages(
    request: Request,
    thread_id: int | str,
    search: str | None = None,
    offset: int | None = None,
    limit: int | None = None,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """List messages from checkpointer.

    Args:
        request: Request object
        payload: List messages schema with configuration and optional filters
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Messages list response with messages data or error
    """
    logger.debug(f"User info: {user}")
    config = {"thread_id": thread_id}

    result = await service.get_messages(
        config,
        user,
        search,
        offset,
        limit,
    )

    return success_response(
        result,
        request,
    )


@router.delete(
    "/v1/threads/{thread_id}/messages/{message_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ResponseSchema),
    summary="Delete message from checkpointer",
    description="Delete a specific message from the checkpointer using configuration and ID.",
)
async def delete_message(
    request: Request,
    message_id: str | int,
    thread_id: str | int,
    payload: ConfigSchema,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Delete message from checkpointer.

    Args:
        request: Request object
        payload: Delete message schema with configuration and message ID
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Success response or error
    """
    logger.debug(f"User info: {user}")
    config = {"thread_id": thread_id}
    if payload.config:
        config.update(payload.config)

    await service.delete_message(
        config,
        user,
        message_id,
    )

    return success_response(
        {"success": True, "message": "Message deleted successfully"},
        request,
    )


# Handle Threads


@router.get(
    "/v1/threads/{thread_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ThreadResponseSchema),
    summary="Get thread from checkpointer",
    description="Retrieve a specific thread from the checkpointer using configuration.",
)
async def get_thread(
    request: Request,
    thread_id: str | int,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Get thread from checkpointer.

    Args:
        request: Request object
        payload: Get thread schema with configuration and thread ID
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Thread response with thread data or error
    """
    logger.debug(f"User info: {user}")

    result = await service.get_thread(
        {"thread_id": thread_id},
        user,
    )

    return success_response(
        {"thread_data": result},
        request,
    )


@router.get(
    "/v1/threads",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ThreadsListResponseSchema),
    summary="List threads from checkpointer",
    description="Retrieve a list of threads from the checkpointer with optional filters.",
)
async def list_threads(
    request: Request,
    search: str | None = None,
    offset: int | None = None,
    limit: int | None = None,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """List threads from checkpointer.

    Args:
        request: Request object
        payload: List threads schema with configuration and optional filters
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Threads list response with threads data or error
    """
    logger.debug(f"User info: {user}")

    result = await service.list_threads(
        user,
        search,
        offset,
        limit,
    )

    return success_response(
        result,
        request,
    )


@router.delete(
    "/v1/threads/{thread_id}",
    status_code=status.HTTP_200_OK,
    responses=generate_swagger_responses(ResponseSchema),
    summary="Delete thread from checkpointer",
    description="Delete a specific thread from the checkpointer using configuration and thread ID.",
)
async def delete_thread(
    request: Request,
    thread_id: str | int,
    payload: ConfigSchema,
    service: CheckpointerService = InjectAPI(CheckpointerService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """Delete thread from checkpointer.

    Args:
        request: Request object
        payload: Delete thread schema with configuration and thread ID
        service: Injected checkpointer service
        user: Current authenticated user

    Returns:
        Success response or error
    """
    logger.debug(f"User info: {user} and thread ID: {thread_id}")

    config = {"thread_id": thread_id}
    if payload.config:
        config.update(payload.config)

    res = await service.delete_thread(
        config,
        user,
        thread_id,
    )

    return success_response(
        res,
        request,
    )
