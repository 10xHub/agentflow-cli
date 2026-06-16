"""Shared client-key derivation for rate limiting.

Used by both the HTTP ``RateLimitMiddleware`` and the WebSocket connection guard so that
WebSocket handshakes are counted against the *same* rate-limit bucket as REST requests.
Works on any ``HTTPConnection`` (both ``Request`` and ``WebSocket`` subclass it).
"""

from starlette.requests import HTTPConnection

from agentflow_cli.src.app.core.config.graph_config import RateLimitConfig


def client_key_for(connection: HTTPConnection, config: RateLimitConfig) -> str:
    """Derive the rate-limit bucket key for a connection, honoring ``by`` and proxy headers."""
    if config.by == "global":
        return "__global__"

    if config.trusted_proxy_headers:
        forwarded_for = connection.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

    client = connection.client
    return client.host if client else "unknown"
