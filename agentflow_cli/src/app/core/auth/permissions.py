"""
Unified authentication and authorization dependency for FastAPI endpoints.

This module provides a reusable dependency that combines authentication and
authorization checks, reducing code duplication across routers.
"""

from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from injectq.integrations import InjectAPI

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.auth_backend import BaseAuth
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.utils.log_sanitizer import sanitize_for_logging


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
        extract_resource_id: Callable[[Request], str | None] | None = None,
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
        request: Request,
        response: Response,
        credential: HTTPAuthorizationCredentials = Depends(
            HTTPBearer(auto_error=False),
        ),
        config: GraphConfig = InjectAPI(GraphConfig),
        auth_backend: BaseAuth = InjectAPI(BaseAuth),
        authz: AuthorizationBackend = InjectAPI(AuthorizationBackend),
    ) -> dict[str, Any]:
        """
        Verify authentication and authorization.

        Returns:
            dict: User information if authenticated and authorized

        Raises:
            HTTPException: 403 if authorization fails
        """
        # Step 1: Authentication (reusing verify_current_user logic)
        user = {}
        backend = config.auth_config()
        if not backend:
            user = {}
        elif not auth_backend:
            logger.error("Auth backend is not configured")
            user = {}
        else:
            user_result = auth_backend.authenticate(
                request,
                response,
                credential,
            )
            if user_result and "user_id" not in user_result:
                logger.error("Authentication failed: 'user_id' not found in user info")
            user = user_result or {}

        # Step 2: Extract resource_id if available
        resource_id = None
        if self.extract_resource_id_fn:
            resource_id = self.extract_resource_id_fn(request)
        else:
            resource_id = self._extract_resource_id_from_path(request)

        # Step 3: Authorization
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

    def _extract_resource_id_from_path(self, request: Request) -> str | None:
        """
        Extract resource ID from request path parameters.

        Looks for common patterns like thread_id, memory_id in path params.

        Args:
            request: FastAPI request object

        Returns:
            Resource ID as string, or None if not found
        """
        # Check path parameters
        path_params = request.path_params

        # Common resource ID patterns
        for param_name in ["thread_id", "memory_id", "namespace"]:
            if param_name in path_params:
                return str(path_params[param_name])

        return None
