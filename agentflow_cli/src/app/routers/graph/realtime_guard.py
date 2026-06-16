"""Connection guard for the WebSocket endpoints.

Rate-limit and request-size middleware are ``BaseHTTPMiddleware`` and Starlette runs them
only for HTTP scopes, so WebSocket handshakes bypass them entirely. This module re-applies
two protections at the handshake, as a FastAPI dependency:

1. The same global rate limit as REST (shared backend + bucket), so opening a socket counts
   like any other request.
2. A per-process cap on concurrent WebSocket connections (``websocket.max_connections`` in
   agentflow.json).

Rejections raise ``WebSocketException`` before ``accept()``, so the handshake fails with a
close code instead of leaving a half-open socket. The concurrency slot is released on
teardown of the (yield) dependency, i.e. when the handler returns or the client disconnects.
"""

from collections.abc import AsyncIterator

from fastapi import WebSocket, WebSocketException
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.middleware.rate_limit.keying import client_key_for


# RFC 6455 close code 1013 "Try Again Later" -- the right signal for shed-load rejections.
WS_TRY_AGAIN_LATER = 1013


class _ConnectionRegistry:
    """Per-process counter of active WebSocket connections.

    The event loop is single-threaded, so the check-and-increment in :meth:`try_acquire` is
    atomic (no ``await`` between the test and the mutation) and needs no lock. This counter is
    per process, matching the in-memory rate-limit backend's scope; for a multi-worker
    deployment, set ``max_connections`` per worker accordingly.
    """

    def __init__(self) -> None:
        self._active = 0

    @property
    def active(self) -> int:
        return self._active

    def try_acquire(self, max_connections: int | None) -> bool:
        if max_connections is not None and self._active >= max_connections:
            return False
        self._active += 1
        return True

    def release(self) -> None:
        if self._active > 0:
            self._active -= 1


# Module-level singleton (per process).
_registry = _ConnectionRegistry()


async def realtime_connection_guard(
    websocket: WebSocket,
    config: GraphConfig = InjectAPI(GraphConfig),
) -> AsyncIterator[None]:
    """Gate a WebSocket handshake on the global rate limit and the concurrent-connection cap."""
    # 1) Shared global rate limit (same backend/bucket as the REST middleware).
    rl_config = config.rate_limit
    backend = getattr(getattr(websocket, "app", None), "state", None)
    backend = getattr(backend, "rate_limit_backend", None)
    if rl_config is not None and backend is not None:
        key = client_key_for(websocket, rl_config)
        decision = await backend.check(key, limit=rl_config.requests, window=rl_config.window)
        if not decision.allowed:
            logger.warning("WebSocket rate limit exceeded for %s", key)
            raise WebSocketException(code=WS_TRY_AGAIN_LATER, reason="Rate limit exceeded")

    # 2) Per-process concurrent-connection cap.
    max_conn = config.websocket.max_connections
    if not _registry.try_acquire(max_conn):
        logger.warning(
            "WebSocket connection limit reached (active=%d, max=%s)",
            _registry.active,
            max_conn,
        )
        raise WebSocketException(code=WS_TRY_AGAIN_LATER, reason="Too many connections")

    try:
        yield
    finally:
        _registry.release()
