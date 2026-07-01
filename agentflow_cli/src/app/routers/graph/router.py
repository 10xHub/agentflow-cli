import asyncio
import contextlib
import json
from typing import Any

from agentflow.core.realtime.base import ErrorEvent
from agentflow.core.realtime.queue import LiveInputQueue
from agentflow.core.state import StreamChunk, StreamEvent
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.logger import logger
from fastapi.responses import StreamingResponse
from injectq.integrations import InjectAPI
from pydantic import ValidationError

from agentflow_cli.src.app.core.auth.permissions import (
    RequirePermission,
    ws_bearer_subprotocol,
)
from agentflow_cli.src.app.routers.graph.realtime_guard import realtime_connection_guard
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    FixGraphRequestSchema,
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphSetupSchema,
    GraphStopSchema,
    WsGraphInputSchema,
)
from agentflow_cli.src.app.routers.graph.services.graph_service import GraphService
from agentflow_cli.src.app.utils import success_response
from agentflow_cli.src.app.utils.swagger_helper import generate_swagger_responses


# Grace period (seconds) to let the model's final response drain to the client after the
# client side ends (``close`` control frame or disconnect). Closing the input queue makes
# the live agent finish its turn and stop once the provider goes idle, so this normally
# returns well within the window; it only bounds a provider that never goes idle.
REALTIME_DRAIN_TIMEOUT = 30.0

# Bound the upstream audio queue. WebSocket frames bypass RequestSizeLimitMiddleware (it is
# HTTP-only), so the realtime path must guard memory itself. At ~50 input frames/sec a depth
# of 1000 is ~20s of buffered audio; if the provider send stalls past that the oldest frames
# are dropped (logged) instead of growing memory without bound -- the audio was already behind.
REALTIME_INPUT_QUEUE_MAXSIZE = 1000

# Hard cap on a single binary (PCM16) input frame. Normal client chunks are tens of KB
# (16kHz PCM16 = 32KB/s); 1 MiB is ~30s of audio in one frame, far beyond any real chunk.
# Oversized frames are dropped rather than enqueued (again, the middleware does not see them).
REALTIME_MAX_FRAME_BYTES = 1024 * 1024


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
    user: dict[str, Any] = Depends(RequirePermission("graph", "invoke")),
):
    """
    Invoke the graph with the provided input and return the final result.
    """
    logger.info(f"Graph invoke request received with {len(graph_input.messages)} messages")

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
    user: dict[str, Any] = Depends(RequirePermission("graph", "stream")),
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
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Encoding": "identity",  # Disable any content encoding (bypasses GZip)
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
    user: dict[str, Any] = Depends(RequirePermission("graph", "read")),
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
    user: dict[str, Any] = Depends(RequirePermission("graph", "read")),
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
    user: dict[str, Any] = Depends(RequirePermission("graph", "stop")),
):
    """
    Stop the graph execution for a specific thread.

    Args:
        stop_request: Request containing thread_id and optional config

    Returns:
        Status information about the stop operation
    """
    logger.info(f"Graph stop request received for thread: {stop_request.thread_id}")

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
    user: dict[str, Any] = Depends(RequirePermission("graph", "setup")),
):
    """
    Setup the graph execution for a specific thread.

    Args:
        setup_request: Request containing thread_id and optional config

    Returns:
        Status information about the setup operation
    """
    logger.info("Graph setup request received")

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
    user: dict[str, Any] = Depends(RequirePermission("graph", "fix")),
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


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ──────────────────────────────────────────────────────────────────────────────


@router.websocket("/v1/graph/ws")
async def websocket_graph(
    websocket: WebSocket,
    _guard: None = Depends(realtime_connection_guard),
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(RequirePermission("graph", "stream")),
):
    """
    WebSocket endpoint for streaming graph execution.

    One connection, one run at a time.  The client drives the protocol:

    Fresh run
    ---------
    Client → Server  :  WsGraphInputSchema { invoke_type:"fresh", messages:[…], config:{} }
    Server → Client  :  StreamChunk JSON messages  (same format as POST /v1/graph/stream)
    Server → Client  :  StreamChunk { event:"updates", data:{status:"done"} }

    Resume after remote tool call
    -----------------------------
    (client detects the remote-tool-call chunk in the stream, executes the tool)
    Client → Server  :  WsGraphInputSchema { invoke_type:"resume", tool_result:[…],
                                             config:{thread_id:"<id>"} }
    Server → Client  :  StreamChunk JSON messages  (graph resumes from checkpoint)
    Server → Client  :  StreamChunk { event:"updates", data:{status:"done"} }

    The server does not inspect chunks for tool-call detection — that is the
    client library's responsibility.  invoke_type is only used for validation
    and logging.

    Authentication
    --------------
    Bearer token via the ``Authorization`` header, the ``agentflow-bearer``
    Sec-WebSocket-Protocol (browser-safe), or the ``?token=`` query fallback —
    identical to the HTTP stream route. Handshakes are subject to the global rate
    limit and the ``websocket.max_connections`` cap.

    Close codes
    -----------
    1000  normal closure (client disconnected cleanly)
    1008  rejected: this graph is a live (realtime) agent — use ``/v1/graph/live``
    1011  unexpected server error
    1013  rejected: rate limit or connection cap exceeded (try again later)
    """
    await websocket.accept(subprotocol=ws_bearer_subprotocol(websocket))
    logger.info("WebSocket graph connection accepted")

    # Wrong agent type for this endpoint: a live (realtime) graph cannot be driven over
    # the turn-based stream socket. Reject up front with a clear error instead of failing
    # mid-run when the graph refuses invoke/stream.
    if service.is_live_agent:
        logger.warning("Rejected /v1/graph/ws connection: graph is a live agent")
        with contextlib.suppress(Exception):
            await websocket.send_text(
                StreamChunk(
                    event=StreamEvent.ERROR,
                    data={
                        "reason": "This graph is a live (realtime) agent; connect to "
                        "/v1/graph/live instead of /v1/graph/ws.",
                    },
                ).model_dump_json()
            )
        with contextlib.suppress(Exception):
            await websocket.close(code=1008)
        return

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break

            try:
                ws_input = WsGraphInputSchema(**data)
            except Exception as e:
                logger.warning("WebSocket received invalid input: %s", e)
                await websocket.send_text(
                    StreamChunk(
                        event=StreamEvent.ERROR,
                        data={"reason": f"Invalid request: {e}"},
                    ).model_dump_json()
                )
                continue

            thread_id = (ws_input.config or {}).get("thread_id", "new")
            logger.info(
                "WebSocket graph run: invoke_type=%s, thread_id=%s",
                ws_input.invoke_type,
                thread_id,
            )

            graph_input = ws_input.to_graph_input()
            async for chunk_json in service.stream_graph(graph_input, user=user):
                await websocket.send_text(chunk_json)

            await websocket.send_text(
                StreamChunk(
                    event=StreamEvent.UPDATES,
                    data={"status": "done"},
                ).model_dump_json()
            )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket graph connection error: %s", e)
        with contextlib.suppress(Exception):
            await websocket.close(code=1011)


def _realtime_event_json(event: Any) -> str:
    """Serialize a non-audio RealtimeEvent to a JSON text frame for the client."""
    try:
        payload = event.model_dump(mode="json")
    except Exception as e:
        logger.warning("Realtime event serialization failed (%s): %s", type(event).__name__, e)
        payload = {"type": getattr(event, "type", "unknown")}
    return json.dumps(payload)


@router.websocket("/v1/graph/live")
async def realtime_graph_ws(  # noqa: PLR0915
    websocket: WebSocket,
    _guard: None = Depends(realtime_connection_guard),
    service: GraphService = InjectAPI(GraphService),
    user: dict[str, Any] = Depends(RequirePermission("graph", "stream")),
):
    """Realtime (audio-to-audio) WebSocket bridge over ``CompiledGraph.arealtime``.

    Protocol (provider-neutral; the client never sees Gemini vs OpenAI)
    ------------------------------------------------------------------
    First frame  : JSON control  ``{model, thread_id?, voice?, modalities?, vad?, ...}``
    Upstream     : binary frame   = PCM16 input audio
                   JSON control   = ``{type:"activity_start"|"activity_end"|"text"|"close", ...}``
    Downstream   : binary frame   = PCM16 model audio (``audio_delta``)
                   JSON text frame = every other event (transcripts, turn_complete,
                                     interrupted, tool_call, session/go_away, error)

    Auth: ``RequirePermission("graph","stream")`` — bearer via the ``Authorization`` header,
    the ``agentflow-bearer`` Sec-WebSocket-Protocol (browser-safe), or the ``?token=`` query
    fallback. Handshakes are subject to the global rate limit and the
    ``websocket.max_connections`` cap (rejected with close code 1013). A non-live
    (turn-based) graph is rejected up front with close code 1008 — use ``/v1/graph/ws``.
    """
    await websocket.accept(subprotocol=ws_bearer_subprotocol(websocket))
    logger.info("Realtime WebSocket connection accepted")

    # Wrong agent type for this endpoint: the realtime bridge requires a graph rooted at a
    # LiveAgent. Reject a turn-based graph up front with a normalized fatal error instead
    # of accepting the init frame and failing later inside ``arealtime``.
    if not service.is_live_agent:
        logger.warning("Rejected /v1/graph/live connection: graph is not a live agent")
        with contextlib.suppress(Exception):
            await websocket.send_text(
                _realtime_event_json(
                    ErrorEvent(
                        code="not_live",
                        message="This graph is not a live (realtime) agent; use the "
                        "turn-based /v1/graph/ws endpoint instead of /v1/graph/live.",
                        fatal=True,
                    )
                )
            )
        with contextlib.suppress(Exception):
            await websocket.close(code=1008)
        return

    try:
        init = await websocket.receive_json()
    except WebSocketDisconnect:
        logger.info("Realtime client disconnected before init")
        return
    except Exception as e:
        logger.warning("Realtime init frame invalid: %s", e)
        with contextlib.suppress(Exception):
            await websocket.close(code=1003)
        return

    if not isinstance(init, dict):
        logger.warning("Realtime init frame must be a JSON object, got %s", type(init).__name__)
        with contextlib.suppress(Exception):
            await websocket.close(code=1003)
        return

    queue = LiveInputQueue(maxsize=REALTIME_INPUT_QUEUE_MAXSIZE)

    async def upstream() -> None:
        """Pump client frames into the input queue until close/disconnect."""
        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                data = message.get("bytes")
                if data is not None:
                    if len(data) > REALTIME_MAX_FRAME_BYTES:
                        logger.warning(
                            "Realtime upstream: dropping oversized audio frame (%d bytes > %d)",
                            len(data),
                            REALTIME_MAX_FRAME_BYTES,
                        )
                        continue
                    queue.send_audio(data)
                    continue
                text = message.get("text")
                if text is None:
                    continue
                try:
                    control = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning("Realtime upstream: non-JSON text frame ignored")
                    continue
                ctype = control.get("type")
                if ctype == "text":
                    queue.send_text(control.get("text", ""))
                elif ctype == "activity_start":
                    queue.send_activity_start()
                elif ctype == "activity_end":
                    queue.send_activity_end()
                elif ctype == "close":
                    break
        except WebSocketDisconnect:
            logger.info("Realtime client disconnected (upstream)")
        finally:
            queue.close()

    async def downstream() -> None:
        """Stream normalized events back: audio as binary, everything else as JSON."""
        try:
            async for event in service.realtime_graph(queue, init, user):
                if getattr(event, "type", None) == "audio_delta":
                    await websocket.send_bytes(event.data)
                else:
                    await websocket.send_text(_realtime_event_json(event))
        except (ValidationError, ValueError) as e:
            # Bad session config from the init frame (e.g. an invalid ``modalities`` value)
            # is a client error, not a server fault. Send a normalized, fatal error event
            # so the client can show why instead of seeing an opaque 1011 close.
            logger.warning("Realtime session config rejected: %s", e)
            with contextlib.suppress(Exception):
                await websocket.send_text(
                    _realtime_event_json(
                        ErrorEvent(code="invalid_config", message=str(e), fatal=True)
                    )
                )

    up_task = asyncio.create_task(upstream())
    down_task = asyncio.create_task(downstream())
    try:
        _done, pending = await asyncio.wait(
            {up_task, down_task}, return_when=asyncio.FIRST_COMPLETED
        )

        # If the client side finished first (sent ``close`` or disconnected) while the
        # model is still responding, give downstream a bounded grace period to drain the
        # session's final events instead of cutting them off. Closing the input queue ends
        # the live agent's turn and stops it once the provider goes idle, so this returns
        # promptly; on a real disconnect the next send fails fast and downstream ends.
        if down_task in pending:
            queue.close()
            await asyncio.wait({down_task}, timeout=REALTIME_DRAIN_TIMEOUT)

        # Cancel whatever is still running: downstream that overran the grace window, or
        # upstream once the session ended.
        for task in (up_task, down_task):
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task

        # asyncio.wait never re-raises; surface any failure from the finished task(s)
        # (e.g. arealtime rejecting a non-live graph, or a provider/checkpointer error).
        for task in (up_task, down_task):
            if task.done() and not task.cancelled():
                task.result()
    except WebSocketDisconnect:
        # The client going away mid-session is a normal termination, not a server fault;
        # don't log it as an error or attempt a 1011 close on an already-closed socket.
        logger.info("Realtime WebSocket client disconnected")
    except Exception as e:
        logger.error("Realtime WebSocket error: %s", e)
        with contextlib.suppress(Exception):
            await websocket.close(code=1011)
    finally:
        queue.close()
        with contextlib.suppress(Exception):
            await websocket.close()
