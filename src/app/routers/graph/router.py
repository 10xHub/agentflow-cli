from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from fastapi_injector import Injected

from src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
)
from src.app.routers.graph.services.graph_service import GraphService
from src.app.utils import success_response


router = APIRouter(
    tags=["Graph"],
)


@router.post(
    "/v1/graph/invoke",
    summary="Invoke graph execution",
    description="Execute the graph with the provided input and return the final result",
    openapi_extra={},
)
async def invoke_graph(
    request: Request,
    graph_input: GraphInputSchema,
    background_tasks: BackgroundTasks,
    service: GraphService = Injected(GraphService),
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    logger.info(f"Graph invoke request received with {len(graph_input.messages)} messages")

    result = await service.invoke_graph(graph_input, background_tasks)

    logger.info("Graph invoke completed successfully")

    return success_response(
        result.model_dump(),
        request,
    )


@router.post(
    "/v1/graph/stream",
    summary="Stream graph execution",
    description="Execute the graph with streaming output for real-time results",
    openapi_extra={},
)
async def stream_graph(
    request: Request,
    graph_input: GraphInputSchema,
    background_tasks: BackgroundTasks,
    service: GraphService = Injected(GraphService),
):
    """
    Stream the graph execution with real-time output.
    """
    logger.info(f"Graph stream request received with {len(graph_input.messages)} messages")

    async def generate_stream():
        """Generator function for streaming graph output."""
        try:
            async for chunk in service.stream_graph(graph_input, background_tasks):
                # Format as server-sent events
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            logger.error(f"Error in stream generation: {e}")
            yield f"data: {{'error': 'Stream generation failed: {e!s}'}}\n\n"
        finally:
            # Send end-of-stream marker
            yield "data: [DONE]\n\n"

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
