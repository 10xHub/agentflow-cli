from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from injectq.integrations import InjectAPI

from src.app.core.auth.auth_backend import verify_current_user
from src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphStreamChunkSchema,
)
from src.app.routers.graph.services.graph_service import GraphService
from src.app.utils import success_response
from src.app.utils.swagger_helper import generate_swagger_responses


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
    background_tasks: BackgroundTasks,
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
        background_tasks,
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
    background_tasks: BackgroundTasks,
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(verify_current_user),
):
    """
    Stream the graph execution with real-time output.
    """
    logger.info(f"Graph stream request received with {len(graph_input.messages)} messages")

    async def generate_stream():
        """Generator function for streaming graph output."""
        try:
            async for chunk in service.stream_graph(
                graph_input,
                user,
                background_tasks,
            ):
                # Format as server-sent events
                yield {"data": chunk.model_dump()}
        except Exception as e:
            logger.error(f"Error in stream generation: {e}")
            yield {"error": f"Stream generation failed: {e!s}"}
        finally:
            # Send end-of-stream marker
            yield {"data": "[DONE]"}

    logger.info("Starting graph stream")

    return StreamingResponse(
        generate_stream(),
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
