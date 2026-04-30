import time

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import RateLimitConfig

from .base import BaseRateLimitBackend


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Backend-agnostic rate-limit middleware."""

    def __init__(
        self,
        app,
        config: RateLimitConfig,
        backend: BaseRateLimitBackend,
    ) -> None:
        super().__init__(app)
        self.config = config
        self.backend = backend
        self._exclude = frozenset(config.exclude_paths)

    def _client_key(self, request: Request) -> str:
        if self.config.by == "global":
            return "__global__"

        if self.config.trusted_proxy_headers:
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()

        client = request.client
        return client.host if client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exclude:
            return await call_next(request)

        key = self._client_key(request)
        decision = await self.backend.check(
            key,
            limit=self.config.requests,
            window=self.config.window,
        )
        reset_at_epoch = int(time.time()) + decision.reset_after

        if not decision.allowed:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "Rate limit exceeded for %s on %s %s",
                key,
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Too many requests. Limit: {self.config.requests} "
                            f"per {self.config.window}s. "
                            f"Retry after {decision.reset_after}s."
                        ),
                        "limit": self.config.requests,
                        "window_seconds": self.config.window,
                        "retry_after_seconds": decision.reset_after,
                    },
                    "metadata": {
                        "request_id": request_id,
                        "status": "error",
                    },
                },
                headers={
                    "Retry-After": str(decision.reset_after),
                    "X-RateLimit-Limit": str(self.config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at_epoch),
                    "X-RateLimit-Reset-After": str(decision.reset_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.requests)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at_epoch)
        response.headers["X-RateLimit-Reset-After"] = str(decision.reset_after)
        return response
