"""Request size limit middleware for DoS protection."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agentflow_cli.src.app.core import logger


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce maximum request body size limits.

    This prevents DoS attacks through excessively large request bodies.

    Args:
        app: The ASGI application
        max_size: Maximum request body size in bytes (default: 10MB)
    """

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
        self.max_size_mb = max_size / (1024 * 1024)

    async def dispatch(self, request: Request, call_next):
        """
        Check request size and reject if too large.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response: Either the normal response or 413 Payload Too Large
        """
        # Get content-length header
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            if content_length > self.max_size:
                logger.warning(
                    f"Request rejected: size {content_length} bytes "
                    f"exceeds limit of {self.max_size} bytes "
                    f"({self.max_size_mb:.1f}MB)"
                )

                # Get request ID if available
                request_id = getattr(request.state, "request_id", "unknown")

                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": (
                                f"Request body too large. "
                                f"Maximum size is {self.max_size_mb:.1f}MB"
                            ),
                            "max_size_bytes": self.max_size,
                            "max_size_mb": self.max_size_mb,
                        },
                        "metadata": {
                            "request_id": request_id,
                            "status": "error",
                        },
                    },
                )

        # Process request normally
        return await call_next(request)
