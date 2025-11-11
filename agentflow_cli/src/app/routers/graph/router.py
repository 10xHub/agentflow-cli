import json
from typing import Any

from agentflow.state import Message, StreamChunk
from agentflow.utils import ResponseGranularity
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core.auth.auth_backend import verify_current_user
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    FixGraphRequestSchema,
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphSetupSchema,
    GraphStopSchema,
)
from agentflow_cli.src.app.routers.graph.services.graph_service import GraphService
from agentflow_cli.src.app.utils import success_response
from agentflow_cli.src.app.utils.file_processor import FileProcessor
from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses


router = APIRouter(
    tags=["Graph"],
)


@router.post(
    "/v1/graph/invoke",
    summary="Invoke graph execution",
    responses=generate_swagger_responses(GraphInvokeOutputSchema),
    description="Execute the graph with the provided input and return the final result",
    openapi_extra={},
)
async def invoke_graph(
    request: Request,
    graph_input: GraphInputSchema,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    logger.info(f"Graph invoke request received with {len(graph_input.messages)} messages")
    logger.debug(f"User info: {user}")

    result: GraphInvokeOutputSchema = await service.invoke_graph(
        graph_input,
        user,
    )

    logger.info("Graph invoke completed successfully")

    return success_response(
        result,
        request,
    )


@router.post(
    "/v1/graph/stream",
    summary="Stream graph execution",
    description="Execute the graph with streaming output for real-time results",
    responses=generate_swagger_responses(StreamChunk),
    openapi_extra={},
)
async def stream_graph(
    graph_input: GraphInputSchema,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Stream the graph execution with real-time output.
    """
    logger.info(f"Graph stream request received with {len(graph_input.messages)} messages")

    result = service.stream_graph(
        graph_input,
        user,
    )

    return StreamingResponse(
        result,
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/v1/graph",
    summary="Invoke graph execution",
    responses=generate_swagger_responses(GraphSchema),
    description="Execute the graph with the provided input and return the final result",
    openapi_extra={},
)
async def graph_details(
    request: Request,
    service: GraphService = InjectAPI(GraphService),
    _: dict[str, Any] = Depends(verify_current_user),
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    logger.info("Graph getting details")

    result: GraphSchema = await service.graph_details()

    logger.info("Graph invoke completed successfully")

    return success_response(
        result,
        request,
    )


@router.get(
    "/v1/graph:StateSchema",
    summary="Invoke graph execution",
    responses=generate_swagger_responses(GraphSchema),
    description="Execute the graph with the provided input and return the final result",
    openapi_extra={},
)
async def state_schema(
    request: Request,
    service: GraphService = InjectAPI(GraphService),
    _: dict[str, Any] = Depends(verify_current_user),
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    logger.info("Graph getting details")

    result: dict = await service.get_state_schema()

    logger.info("Graph invoke completed successfully")

    return success_response(
        result,
        request,
    )


@router.post(
    "/v1/graph/stop",
    summary="Stop graph execution",
    description="Stop the currently running graph execution for a specific thread",
    responses=generate_swagger_responses(dict),  # type: ignore
    openapi_extra={},
)
async def stop_graph(
    request: Request,
    stop_request: GraphStopSchema,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Stop the graph execution for a specific thread.

    Args:
        stop_request: Request containing thread_id and optional config

    Returns:
        Status information about the stop operation
    """
    logger.info(f"Graph stop request received for thread: {stop_request.thread_id}")
    logger.debug(f"User info: {user}")

    result = await service.stop_graph(stop_request.thread_id, user, stop_request.config)

    logger.info(f"Graph stop completed for thread {stop_request.thread_id}")

    return success_response(
        result,
        request,
    )


@router.post(
    "/v1/graph/setup",
    summary="Setup Remote Tool to the Graph Execution",
    description="Stop the currently running graph execution for a specific thread",
    responses=generate_swagger_responses(dict),  # type: ignore
    openapi_extra={},
)
async def setup_graph(
    request: Request,
    setup_request: GraphSetupSchema,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Setup the graph execution for a specific thread.

    Args:
        setup_request: Request containing thread_id and optional config

    Returns:
        Status information about the setup operation
    """
    logger.info("Graph setup request received")
    logger.debug(f"User info: {user}")

    result = await service.setup(setup_request)

    logger.info("Graph setup completed")

    return success_response(
        result,
        request,
    )


@router.post(
    "/v1/graph/fix",
    summary="Fix graph state by removing messages with empty tool calls",
    description=(
        "Fix the graph state by identifying and removing messages that have tool "
        "calls with empty content. This is useful for cleaning up incomplete "
        "tool call messages that may have failed or been interrupted."
    ),
    responses=generate_swagger_responses(dict),  # type: ignore
    openapi_extra={},
)
async def fix_graph(
    request: Request,
    fix_request: FixGraphRequestSchema,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Fix the graph execution state for a specific thread.

    This endpoint removes messages with empty tool call content from the state.
    Tool calls with empty content typically indicate interrupted or failed tool
    executions that should be cleaned up.

    Args:
        request: HTTP request object
        fix_request: Request containing thread_id and optional config
        service: Injected GraphService instance
        user: Current authenticated user

    Returns:
        Status information about the fix operation, including:
        - success: Whether the operation was successful
        - message: Descriptive message about the operation
        - removed_count: Number of messages that were removed
        - state: Updated state after fixing (or original if no changes)

    Raises:
        HTTPException: If the fix operation fails or if no state is found
            for the given thread_id
    """
    logger.info(f"Graph fix request received for thread: {fix_request.thread_id}")
    logger.debug(f"User info: {user}")

    result = await service.fix_graph(
        fix_request.thread_id,
        user,
        fix_request.config,
    )

    logger.info(f"Graph fix completed for thread {fix_request.thread_id}")

    return success_response(
        result,
        request,
    )


@router.post(
    "/v1/graph/invoke-with-files",
    summary="Invoke graph execution with file uploads",
    responses=generate_swagger_responses(GraphInvokeOutputSchema),
    description=(
        "Execute the graph with file uploads and text input. "
        "Files will be processed and included in messages."
    ),
    openapi_extra={},
)
async def invoke_graph_with_files(
    request: Request,
    messages_json: str = Form(..., description="JSON string of messages"),
    initial_state: str | None = Form(None, description="JSON string of initial state"),
    config: str | None = Form(None, description="JSON string of configuration"),
    recursion_limit: int = Form(25, description="Maximum recursion limit"),
    response_granularity: str = Form("low", description="Response granularity (low/partial/full)"),
    extract_text: bool = Form(
        False,
        description="Whether to extract text from documents (requires textxtract library)",
    ),
    files: list[UploadFile] = File(
        default=[], description="Files to upload and include in messages"
    ),
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Invoke the graph with file uploads and return the final result.

    This endpoint allows uploading files along with messages. Files will be processed
    and converted into appropriate ContentBlock types (TextBlock, ImageBlock, DocumentBlock)
    based on their type and the extract_text flag.

    Args:
        request: HTTP request
        messages_json: JSON string of Message objects
        initial_state: Optional JSON string of initial state
        config: Optional JSON string of configuration
        recursion_limit: Maximum recursion limit for graph execution
        response_granularity: Granularity of response
        extract_text: Whether to extract text from documents (requires textxtract[all])
        files: List of files to upload
        service: Injected GraphService
        user: Authenticated user info

    Returns:
        Graph execution result with processed messages including file content
    """
    logger.info(
        f"Graph invoke with files request received. "
        f"Files: {len(files)}, Extract text: {extract_text}"
    )

    # Parse JSON inputs
    try:
        messages_list = json.loads(messages_json)
        messages = [Message(**msg) if isinstance(msg, dict) else msg for msg in messages_list]
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse messages JSON: {e}")
        raise ValueError(f"Invalid messages JSON: {e}") from e

    initial_state_dict = None
    if initial_state:
        try:
            initial_state_dict = json.loads(initial_state)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse initial_state JSON: {e}")
            raise ValueError(f"Invalid initial_state JSON: {e}") from e

    config_dict = None
    if config:
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            raise ValueError(f"Invalid config JSON: {e}") from e

    # Process uploaded files
    file_processor = FileProcessor()
    content_blocks = []

    if files:
        content_blocks = await file_processor.process_multiple_files(files, extract_text)
        logger.info(f"Processed {len(content_blocks)} file(s) into content blocks")

    # Add content blocks to messages
    if content_blocks:
        # Add files to the last user message if it exists, otherwise create a new message
        if messages and messages[-1].role == "user":
            # Append to last user message's content
            messages[-1].content.extend(content_blocks)
        else:
            # Create a new user message with file content blocks
            file_message = Message(
                role="user",
                content=content_blocks,
            )
            messages.append(file_message)

    # Create GraphInputSchema
    graph_input = GraphInputSchema(
        messages=messages,
        initial_state=initial_state_dict,
        config=config_dict,
        recursion_limit=recursion_limit,
        response_granularity=ResponseGranularity(response_granularity.upper()),
    )

    # Execute graph
    result: GraphInvokeOutputSchema = await service.invoke_graph(graph_input, user)

    logger.info("Graph invoke with files completed successfully")

    return success_response(result, request)


@router.post(
    "/v1/graph/stream-with-files",
    summary="Stream graph execution with file uploads",
    description="Execute the graph with file uploads and streaming output for real-time results",
    responses=generate_swagger_responses(StreamChunk),
    openapi_extra={},
)
async def stream_graph_with_files(
    messages_json: str = Form(..., description="JSON string of messages"),
    initial_state: str | None = Form(None, description="JSON string of initial state"),
    config: str | None = Form(None, description="JSON string of configuration"),
    recursion_limit: int = Form(25, description="Maximum recursion limit"),
    response_granularity: str = Form("low", description="Response granularity (low/partial/full)"),
    extract_text: bool = Form(
        False,
        description="Whether to extract text from documents (requires textxtract library)",
    ),
    files: list[UploadFile] = File(
        default=[], description="Files to upload and include in messages"
    ),
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Stream the graph execution with file uploads and real-time output.

    This endpoint allows uploading files along with messages and streams the execution
    results in real-time. Files will be processed and converted into appropriate
    ContentBlock types based on their type and the extract_text flag.

    Args:
        messages_json: JSON string of Message objects
        initial_state: Optional JSON string of initial state
        config: Optional JSON string of configuration
        recursion_limit: Maximum recursion limit for graph execution
        response_granularity: Granularity of response
        extract_text: Whether to extract text from documents (requires textxtract[all])
        files: List of files to upload
        service: Injected GraphService
        user: Authenticated user info

    Returns:
        Streaming response with graph execution chunks
    """
    logger.info(
        f"Graph stream with files request received. "
        f"Files: {len(files)}, Extract text: {extract_text}"
    )

    # Parse JSON inputs
    try:
        messages_list = json.loads(messages_json)
        messages = [Message(**msg) if isinstance(msg, dict) else msg for msg in messages_list]
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse messages JSON: {e}")
        raise ValueError(f"Invalid messages JSON: {e}") from e

    initial_state_dict = None
    if initial_state:
        try:
            initial_state_dict = json.loads(initial_state)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse initial_state JSON: {e}")
            raise ValueError(f"Invalid initial_state JSON: {e}") from e

    config_dict = None
    if config:
        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            raise ValueError(f"Invalid config JSON: {e}") from e

    # Process uploaded files
    file_processor = FileProcessor()
    content_blocks = []

    if files:
        content_blocks = await file_processor.process_multiple_files(files, extract_text)
        logger.info(f"Processed {len(content_blocks)} file(s) into content blocks")

    # Add content blocks to messages
    if content_blocks:
        # Add files to the last user message if it exists, otherwise create a new message
        if messages and messages[-1].role == "user":
            # Append to last user message's content
            messages[-1].content.extend(content_blocks)
        else:
            # Create a new user message with file content blocks
            file_message = Message(
                role="user",
                content=content_blocks,
            )
            messages.append(file_message)

    # Create GraphInputSchema
    graph_input = GraphInputSchema(
        messages=messages,
        initial_state=initial_state_dict,
        config=config_dict,
        recursion_limit=recursion_limit,
        response_granularity=ResponseGranularity(response_granularity.upper()),
    )

    # Stream graph execution
    result = service.stream_graph(graph_input, user)

    return StreamingResponse(
        result,
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
