from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core.auth.auth_backend import verify_current_user
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphSetupSchema,
    GraphStopSchema,
    GraphStreamChunkSchema,
)
from agentflow_cli.src.app.routers.graph.services.graph_service import GraphService
from agentflow_cli.src.app.utils import success_response
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
    responses=generate_swagger_responses(GraphStreamChunkSchema),
    openapi_extra={},
)
async def stream_graph(
    request: Request,
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


# @router.post(
#     "/v1/graph/stop",
#     summary="Setup Remote Tool to the Graph Execution",
#     description="Stop the currently running graph execution for a specific thread",
#     responses=generate_swagger_responses(dict),  # type: ignore
#     openapi_extra={},
# )
# async def setup_graph(
#     request: Request,
#     setup_request: GraphSetupSchema,
#     service: GraphService = InjectAPI(GraphService),
#     user: dict[str, Any] = Depends(verify_current_user),
# ):
#     """
#     Setup the graph execution for a specific thread.

#     Args:
#         setup_request: Request containing thread_id and optional config

#     Returns:
#         Status information about the setup operation
#     """
#     logger.info(f"Graph setup request received for thread: {setup_request.thread_id}")
#     logger.debug(f"User info: {user}")

#     result = await service.setup_graph(setup_request.thread_id, user, setup_request.config)

#     logger.info(f"Graph setup completed for thread {setup_request.thread_id}")

#     return success_response(
#         result,
#         request,
#     )
