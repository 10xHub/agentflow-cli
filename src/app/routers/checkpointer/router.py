"""Checkpointer router module."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.app.routers.checkpointer.schemas.checkpointer_schemas import (
    CheckpointerResponseSchema,
    CleanupSchema,
    DeleteMessageSchema,
    GetMessageSchema,
    ListMessagesSchema,
    MessageResponseSchema,
    MessagesListResponseSchema,
    PutMessagesSchema,
    StateResponseSchema,
    StateSchema,
)
from src.app.routers.checkpointer.services.checkpointer_service import CheckpointerService
from src.app.utils.response_helper import create_response_model

router = APIRouter(prefix="/checkpointer", tags=["checkpointer"])


@router.post(
    "/get-state",
    response_model=create_response_model(StateResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Get state from checkpointer",
    description="Retrieve state data from the checkpointer using configuration.",
)
async def get_state(
    request: StateSchema, checkpointer=Depends(get_checkpointer)
) -> StateResponseSchema:
    """Get state from checkpointer.

    Args:
        request: State schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        State response with state data or error
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.get_state(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get state: {e!s}"
        )


@router.post(
    "/put-state",
    response_model=create_response_model(StateResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Put state to checkpointer",
    description="Store state data in the checkpointer using configuration.",
)
async def put_state(
    request: StateSchema, checkpointer=Depends(get_checkpointer)
) -> StateResponseSchema:
    """Put state to checkpointer.

    Args:
        request: State schema with configuration and state data
        checkpointer: Injected checkpointer instance

    Returns:
        State response indicating success or failure
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.put_state(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to put state: {e!s}"
        )


@router.post(
    "/clear-state",
    response_model=create_response_model(CheckpointerResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Clear state from checkpointer",
    description="Clear state data from the checkpointer using configuration.",
)
async def clear_state(
    request: StateSchema, checkpointer=Depends(get_checkpointer)
) -> CheckpointerResponseSchema:
    """Clear state from checkpointer.

    Args:
        request: State schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        Response indicating success or failure
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.clear_state(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear state: {e!s}",
        )


@router.post(
    "/put-messages",
    response_model=create_response_model(CheckpointerResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Put messages to checkpointer",
    description="Store messages in the checkpointer using configuration.",
)
async def put_messages(
    request: PutMessagesSchema, checkpointer=Depends(get_checkpointer)
) -> CheckpointerResponseSchema:
    """Put messages to checkpointer.

    Args:
        request: Put messages schema with configuration and messages
        checkpointer: Injected checkpointer instance

    Returns:
        Response indicating success or failure
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.put_messages(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to put messages: {e!s}",
        )


@router.post(
    "/get-message",
    response_model=create_response_model(MessageResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Get message from checkpointer",
    description="Retrieve a message from the checkpointer using configuration.",
)
async def get_message(
    request: GetMessageSchema, checkpointer=Depends(get_checkpointer)
) -> MessageResponseSchema:
    """Get message from checkpointer.

    Args:
        request: Get message schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        Message response with message data or error
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.get_message(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message: {e!s}",
        )


@router.post(
    "/list-messages",
    response_model=create_response_model(MessagesListResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="List messages from checkpointer",
    description="Retrieve a list of messages from the checkpointer using configuration.",
)
async def list_messages(
    request: ListMessagesSchema, checkpointer=Depends(get_checkpointer)
) -> MessagesListResponseSchema:
    """List messages from checkpointer.

    Args:
        request: List messages schema with configuration and filters
        checkpointer: Injected checkpointer instance

    Returns:
        Messages list response with messages data or error
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.list_messages(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list messages: {e!s}",
        )


@router.post(
    "/delete-message",
    response_model=create_response_model(CheckpointerResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Delete message from checkpointer",
    description="Delete a message from the checkpointer using configuration.",
)
async def delete_message(
    request: DeleteMessageSchema, checkpointer=Depends(get_checkpointer)
) -> CheckpointerResponseSchema:
    """Delete message from checkpointer.

    Args:
        request: Delete message schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        Response indicating success or failure
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.delete_message(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete message: {e!s}",
        )


@router.post(
    "/cleanup",
    response_model=create_response_model(CheckpointerResponseSchema),
    status_code=status.HTTP_200_OK,
    summary="Cleanup checkpointer",
    description="Perform cleanup operations on the checkpointer.",
)
async def cleanup(
    request: CleanupSchema, checkpointer=Depends(get_checkpointer)
) -> CheckpointerResponseSchema:
    """Cleanup checkpointer.

    Args:
        request: Cleanup schema with configuration
        checkpointer: Injected checkpointer instance

    Returns:
        Response indicating success or failure
    """
    try:
        service = CheckpointerService(checkpointer)
        result = await service.cleanup(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to cleanup: {e!s}"
        )
