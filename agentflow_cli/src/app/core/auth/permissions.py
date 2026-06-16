"""
Unified authentication and authorization dependency for FastAPI endpoints.

This module provides a reusable dependency that combines authentication and
authorization checks, reducing code duplication across routers.
"""

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from injectq.integrations import InjectAPI
from starlette.requests import HTTPConnection

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.auth_backend import BaseAuth
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.utils.log_sanitizer import sanitize_for_logging


# Sec-WebSocket-Protocol sentinel carrying the bearer token for browser WebSocket clients.
# The client offers two subprotocols: this sentinel followed by the raw JWT, e.g.
#   new WebSocket(url, ["agentflow-bearer", "<jwt>"])
# The token rides in a request header, so -- unlike ``?token=`` -- it never lands in URLs,
# access logs, or browser history. The server must echo the sentinel on accept() (see
# ``ws_bearer_subprotocol``) or browsers fail the handshake.
WS_BEARER_SUBPROTOCOL = "agentflow-bearer"

# A bearer-carrying Sec-WebSocket-Protocol offer is exactly [sentinel, token].
_BEARER_SUBPROTOCOL_PARTS = 2


def _subprotocols(connection: HTTPConnection) -> list[str]:
    header = connection.headers.get("sec-websocket-protocol")
    if not header:
        return []
    return [p.strip() for p in header.split(",") if p.strip()]


def ws_bearer_subprotocol(connection: HTTPConnection) -> str | None:
    """Return the subprotocol to echo on ``accept()`` when the client used it for the token.

    Browsers require the server to confirm one of the offered subprotocols; when the bearer
    sentinel was offered, accept with it. Returns ``None`` otherwise (plain ``accept()``).
    """
    parts = _subprotocols(connection)
    if parts and parts[0] == WS_BEARER_SUBPROTOCOL:
        return WS_BEARER_SUBPROTOCOL
    return None


def _extract_credential(
    connection: HTTPConnection,
) -> HTTPAuthorizationCredentials | None:
    """Extract bearer credentials from a request or WebSocket connection.

    Mirrors ``HTTPBearer(auto_error=False)`` but works for both HTTP and WebSocket routes
    (FastAPI cannot inject ``HTTPBearer`` on a WebSocket route). Token sources, most secure
    first:

    1. ``Authorization: Bearer <token>`` header -- for non-browser clients.
    2. ``Sec-WebSocket-Protocol: agentflow-bearer, <token>`` -- browser-settable and kept out
       of URLs/logs; the preferred browser mechanism.
    3. ``?token=<token>`` query parameter -- last-resort fallback; the token is exposed in
       URLs/access logs/history, so prefer (2) for browser clients.
    """
    authorization = connection.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)

    # [sentinel, token] -- the two subprotocols a browser client offers to carry the bearer.
    parts = _subprotocols(connection)
    if len(parts) >= _BEARER_SUBPROTOCOL_PARTS and parts[0] == WS_BEARER_SUBPROTOCOL and parts[1]:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=parts[1])

    ws_token = connection.query_params.get("token")
    if ws_token:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=ws_token)

    return None


class RequirePermission:
    """
    FastAPI dependency that combines authentication and authorization.

    This class-based dependency verifies user authentication and checks
    authorization in a single step, reducing boilerplate code in endpoints.

    Usage:
        @router.post("/v1/resource")
        async def endpoint(
            user: dict = Depends(RequirePermission("resource", "action"))
        ):
            # User is authenticated and authorized
            pass

    Args:
        resource: Resource type being accessed (e.g., "graph", "checkpointer", "store")
        action: Action being performed (e.g., "invoke", "read", "write", "delete")
        extract_resource_id: Optional function to extract resource_id from request
    """

    def __init__(
        self,
        resource: str,
        action: str,
        extract_resource_id: Callable[[HTTPConnection], str | None] | None = None,
    ):
        """
        Initialize the permission requirement.

        Args:
            resource: Resource type (graph, checkpointer, store)
            action: Action type (invoke, stream, read, write, delete, etc.)
            extract_resource_id: Optional callable that extracts resource_id from request
        """
        self.resource = resource
        self.action = action
        self.extract_resource_id_fn = extract_resource_id

    async def __call__(
        self,
        connection: HTTPConnection,
        response: Response,
        config: GraphConfig = InjectAPI(GraphConfig),
        auth_backend: BaseAuth = InjectAPI(BaseAuth),
        authz: AuthorizationBackend = InjectAPI(AuthorizationBackend),
    ) -> dict[str, Any]:
        """
        Verify authentication and authorization.

        ``connection`` is typed as ``HTTPConnection`` (the common base of ``Request``
        and ``WebSocket``) so this dependency resolves on both HTTP and WebSocket
        routes; FastAPI cannot inject a ``Request`` on a WebSocket route.

        Returns:
            dict: User information if authenticated and authorized

        Raises:
            HTTPException: 403 if authorization fails
        """
        # Extract bearer credentials from the Authorization header, with a
        # ``?token=`` query fallback for browser WebSocket clients (see
        # _extract_credential). Works for both HTTP and WebSocket connections.
        credential = _extract_credential(connection)

        # Step 1: Check if auth is configured
        backend = config.auth_config()

        # If auth is not configured, skip authentication and authorization entirely
        if not backend:
            logger.debug(
                f"Auth not configured, skipping auth/authz for {self.resource}:{self.action}"
            )
            return {}

        # Step 2: Authentication (reusing verify_current_user logic)
        user = {}
        if not auth_backend:
            logger.error("Auth backend is not configured")
            user = {}
        else:
            user_result = auth_backend.authenticate(
                connection,
                response,
                credential,
            )
            if user_result and "user_id" not in user_result:
                logger.error("Authentication failed: 'user_id' not found in user info")
            user = user_result or {}

        # Step 3: Extract resource_id if available
        resource_id = None
        if self.extract_resource_id_fn:
            resource_id = self.extract_resource_id_fn(connection)
        else:
            resource_id = self._extract_resource_id_from_path(connection)

        # Step 4: Authorization
        if not await authz.authorize(
            user,
            self.resource,
            self.action,
            resource_id=resource_id,
        ):
            logger.warning(
                f"Authorization failed for user {user.get('user_id')} "
                f"on {self.resource}:{self.action}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to {self.action} {self.resource}",
            )

        # Log successful auth/authz (with sanitized user info)
        logger.debug(
            f"Auth/Authz success for {self.resource}:{self.action}, "
            f"user: {sanitize_for_logging(user)}"
        )

        return user

    def _extract_resource_id_from_path(self, connection: HTTPConnection) -> str | None:
        """
        Extract resource ID from request path parameters.

        Looks for common patterns like thread_id, memory_id in path params.

        Args:
            connection: FastAPI request or WebSocket connection

        Returns:
            Resource ID as string, or None if not found
        """
        # Check path parameters
        path_params = connection.path_params

        # Common resource ID patterns
        for param_name in ["thread_id", "memory_id", "namespace"]:
            if param_name in path_params:
                return str(path_params[param_name])

        return None
