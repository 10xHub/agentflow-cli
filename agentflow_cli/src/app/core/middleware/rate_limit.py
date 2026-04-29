"""In-memory sliding-window rate limit middleware.

Configured via ``agentflow.json``::

    "rate_limit": {
        "enabled": true,
        "requests": 100,
        "window": 60,
        "by": "ip"
    }

Fields
------
enabled  : bool  – turn the limiter on/off without removing the key.
requests : int   – max requests allowed in the window.
window   : int   – rolling window duration in seconds.
by       : str   – "ip" (per client IP) or "global" (single shared bucket).
"""

import asyncio
import time
from collections import deque

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import RateLimitConfig


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter middleware.

    Args:
        app:    The ASGI application.
        config: Parsed :class:`RateLimitConfig` from ``agentflow.json``.
    """

    def __init__(self, app, config: RateLimitConfig) -> None:
        super().__init__(app)
        self.config = config
        # bucket key -> deque of request timestamps (float, epoch seconds)
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bucket_key(self, request: Request) -> str:
        if self.config.by == "global":
            return "__global__"
        # Per-IP: honour X-Forwarded-For when behind a proxy, fall back to
        # the direct client address.
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def _is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Check whether the request is within the rate limit.

        Returns
        -------
        (allowed, remaining, reset_in_seconds)
        """
        now = time.monotonic()
        window_start = now - self.config.window

        async with self._lock:
            bucket = self._buckets.setdefault(key, deque())

            # Drop timestamps that fell outside the current window.
            while bucket and bucket[0] < window_start:
                bucket.popleft()

            count = len(bucket)
            remaining = max(0, self.config.requests - count - 1)

            if count >= self.config.requests:
                # How long until the oldest entry expires.
                reset_in = int(self.config.window - (now - bucket[0])) + 1
                return False, 0, reset_in

            bucket.append(now)
            return True, remaining, self.config.window

    # ------------------------------------------------------------------
    # Middleware dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next):
        key = self._bucket_key(request)
        allowed, remaining, reset_in = await self._is_allowed(key)

        if not allowed:
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
                            f"Too many requests. Limit is {self.config.requests} "
                            f"requests per {self.config.window}s. "
                            f"Retry after {reset_in}s."
                        ),
                        "limit": self.config.requests,
                        "window_seconds": self.config.window,
                        "retry_after_seconds": reset_in,
                    },
                    "metadata": {
                        "request_id": request_id,
                        "status": "error",
                    },
                },
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(self.config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response
