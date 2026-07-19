"""Shared client-key derivation for rate limiting.

Used by both the HTTP ``RateLimitMiddleware`` and the WebSocket connection guard so that
WebSocket handshakes are counted against the *same* rate-limit bucket as REST requests.
Works on any ``HTTPConnection`` (both ``Request`` and ``WebSocket`` subclass it).
"""

import logging

from starlette.requests import HTTPConnection

from agentflow_cli.src.app.core.config.graph_config import RateLimitConfig


logger = logging.getLogger("agentflow_api")


def _client_ip(connection: HTTPConnection, config: RateLimitConfig) -> str:
    """Resolve the client IP, honouring X-Forwarded-For only where it is trustworthy.

    ``X-Forwarded-For`` is a list that each proxy APPENDS to. Whatever the caller
    sent arrives at the left; only the entries your own proxies appended, on the
    right, are trustworthy.

    Reading ``split(",")[0]`` -- the previous behaviour -- therefore took a value
    the caller fully controls. An attacker could send a different
    ``X-Forwarded-For`` on every request, land in a fresh bucket each time, and
    never be rate limited at all.

    We instead count ``trusted_proxy_hops`` back from the RIGHT. With one proxy in
    front (the default), the last entry is the address that proxy actually observed
    -- the real peer.
    """
    if config.trusted_proxy_headers:
        forwarded_for = connection.headers.get("X-Forwarded-For")
        if forwarded_for:
            parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
            hops = max(1, getattr(config, "trusted_proxy_hops", 1))
            if len(parts) >= hops:
                return parts[-hops]
            # Fewer entries than our own infrastructure should have appended: the
            # header is not shaped the way we expect, so trust none of it.
            logger.warning(
                "X-Forwarded-For has %d entries but %d trusted proxy hop(s) are "
                "configured; ignoring the header and using the peer address.",
                len(parts),
                hops,
            )

    client = connection.client
    return client.host if client else "unknown"


def client_key_for(connection: HTTPConnection, config: RateLimitConfig) -> str:
    """Derive the rate-limit bucket key for a connection.

    Supports ``by``:

    - ``"global"``: a single bucket for the whole service.
    - ``"user"``: one bucket per authenticated user. This is what you want once auth
      is enabled: limiting purely by IP gives one user roaming across addresses an
      unlimited budget, while a NAT'd office sharing one address gets throttled as
      though it were a single caller.
    - ``"ip"``: one bucket per client address (the default).

    ``"user"`` falls back to the peer address when there is no authenticated user,
    so anonymous traffic is still limited per-caller rather than sharing one bucket
    that any single client could exhaust for everybody.
    """
    if config.by == "global":
        return "__global__"

    if config.by == "user":
        state = getattr(connection, "state", None)
        user = getattr(state, "user", None) if state is not None else None
        if isinstance(user, dict):
            user_id = user.get("user_id")
            if user_id:
                return f"user:{user_id}"
        return f"ip:{_client_ip(connection, config)}"

    return _client_ip(connection, config)
