import json
import logging
import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from dotenv import load_dotenv


logger = logging.getLogger("agentflow_api")


def _parse_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field} must be a boolean")


def _expand_env(value: str | None) -> str | None:
    if value is None:
        return None
    expanded = os.path.expandvars(value)
    if expanded == value and (value.startswith("$") or "${" in value):
        raise ValueError(f"Unresolved environment variable in value: {value}")
    return expanded


@dataclass
class RateLimitConfig:
    """Rate limit configuration parsed from agentflow.json.

    Example (memory backend, default)::

        "rate_limit": {
            "enabled": true,
            "backend": "memory",
            "requests": 100,
            "window": 60,
            "by": "ip",
            "trusted_proxy_headers": false,
            "exclude_paths": ["/health", "/docs", "/redoc", "/openapi.json"]
        }

    Example (Redis backend)::

        "rate_limit": {
            "enabled": true,
            "backend": "redis",
            "requests": 100,
            "window": 60,
            "by": "ip",
            "trusted_proxy_headers": true,
            "exclude_paths": ["/health"],
            "redis": {
                "url": "redis://localhost:6379/0",
                "prefix": "agentflow:rate-limit"
            },
            "fail_open": true
        }

    Example (custom backend)::

        "rate_limit": {
            "enabled": true,
            "backend": "custom",
            "requests": 100,
            "window": 60,
            "by": "ip"
        }

    For custom backends, bind a ``BaseRateLimitBackend`` instance in InjectQ.
    """

    enabled: bool
    requests: int
    window: int
    by: str  # "ip" | "user" | "global"
    backend: str  # "memory" | "redis" | "custom"
    redis_url: str | None
    redis_prefix: str
    exclude_paths: tuple[str, ...]
    trusted_proxy_headers: bool  # honour X-Forwarded-For only when True
    # Number of proxies you control in front of the app. Only this many entries,
    # counted from the RIGHT of X-Forwarded-For, were appended by your own
    # infrastructure; anything further left came from the caller and is forgeable.
    trusted_proxy_hops: int = 1
    fail_open: bool = True  # on backend error: True=allow, False=deny

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitConfig":
        if not isinstance(data, dict):
            raise ValueError("rate_limit must be an object")

        enabled = _parse_bool(data.get("enabled", True), field="rate_limit.enabled")
        requests = int(data.get("requests", 100))
        window = int(data.get("window", 60))
        by = data.get("by", "ip")
        backend = data.get("backend", "memory")
        trusted_proxy_headers = _parse_bool(
            data.get("trusted_proxy_headers", False),
            field="rate_limit.trusted_proxy_headers",
        )
        exclude_paths_raw = data.get("exclude_paths", [])
        if not isinstance(exclude_paths_raw, list | tuple):
            raise ValueError("rate_limit.exclude_paths must be a list of paths")
        exclude_paths = tuple(str(path) for path in exclude_paths_raw)
        fail_open = _parse_bool(data.get("fail_open", True), field="rate_limit.fail_open")

        # Redis sub-object: {"url": "...", "prefix": "..."}
        redis_obj = data.get("redis") or {}
        if isinstance(redis_obj, str):
            # Allow shorthand: "redis": "redis://..."
            redis_url: str | None = _expand_env(redis_obj)
            redis_prefix = "agentflow:rate-limit"
        elif isinstance(redis_obj, dict):
            redis_url = _expand_env(redis_obj.get("url") or None)
            redis_prefix = str(redis_obj.get("prefix", "agentflow:rate-limit"))
        else:
            raise ValueError("rate_limit.redis must be an object or Redis URL string")

        # How many proxies of YOUR OWN sit in front of the app and append to
        # X-Forwarded-For. Only that many entries, counted from the right, were
        # written by infrastructure you control; everything to the left of them came
        # from the caller and is forgeable. See keying._client_ip.
        trusted_proxy_hops = int(data.get("trusted_proxy_hops", 1))

        # Validation
        if by not in ("ip", "global", "user"):
            raise ValueError(f"rate_limit.by must be 'ip', 'user', or 'global', got '{by}'")
        if backend not in ("memory", "redis", "custom"):
            raise ValueError(
                f"rate_limit.backend must be 'memory', 'redis', or 'custom', got '{backend}'"
            )
        if requests <= 0:
            raise ValueError("rate_limit.requests must be a positive integer")
        if window <= 0:
            raise ValueError("rate_limit.window must be a positive integer")
        if trusted_proxy_hops < 1:
            raise ValueError("rate_limit.trusted_proxy_hops must be >= 1")

        # The memory backend counts per PROCESS. Under gunicorn with N workers the
        # effective limit therefore becomes requests x N, and it resets whenever a
        # worker restarts -- so it does not really limit anything in production.
        if enabled and backend == "memory":
            logger.warning(
                "Rate limiting uses the in-memory backend. It counts per process, so "
                "with N workers the real limit is requests x N and it resets on every "
                "worker restart. Use the 'redis' backend for any multi-worker deployment."
            )

        return cls(
            enabled=enabled,
            requests=requests,
            window=window,
            by=by,
            backend=backend,
            redis_url=redis_url,
            redis_prefix=redis_prefix,
            exclude_paths=exclude_paths,
            trusted_proxy_headers=trusted_proxy_headers,
            trusted_proxy_hops=trusted_proxy_hops,
            fail_open=fail_open,
        )


@dataclass
class WebSocketConfig:
    """WebSocket settings parsed from agentflow.json.

    Example::

        "websocket": {
            "enabled": true,
            "max_connections": 100
        }

    ``enabled`` (default ``true``) controls whether the streaming endpoint
    ``/v1/graph/ws`` is mounted at all. Setting it to ``false`` removes the route, so the
    handshake is refused by Starlette (HTTP 403) before any handler, dependency or auth code
    runs -- the right switch for a deployment that only uses REST/SSE and does not want the
    extra surface. It does not affect the realtime bridge ``/v1/graph/live``, which already
    rejects non-live graphs, nor the SSE endpoint ``/v1/graph/stream``.

    ``max_connections`` caps the number of concurrent WebSocket connections this server
    *process* accepts (realtime ``/v1/graph/live`` + streaming ``/v1/graph/ws``). ``None`` or
    ``0`` means unlimited. It is a per-process limit, like the in-memory rate-limit backend;
    run one limiter per worker. WebSocket handshakes are also subject to the global
    ``rate_limit`` (they share the same bucket as REST requests), since rate-limit middleware
    is HTTP-only and cannot see WebSocket scopes.
    """

    max_connections: int | None
    enabled: bool = True
    # Whether ``enabled`` was written in the file, as opposed to defaulting to True. Only a
    # written value can conflict with routers.websocket; a default must not.
    enabled_declared: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "WebSocketConfig":
        if not isinstance(data, dict):
            raise ValueError("websocket must be an object")
        enabled = _parse_bool(data.get("enabled", True), field="websocket.enabled")
        declared = "enabled" in data
        raw = data.get("max_connections")
        if raw in (None, 0):
            return cls(max_connections=None, enabled=enabled, enabled_declared=declared)
        max_connections = int(raw)
        if max_connections < 0:
            raise ValueError("websocket.max_connections must be a non-negative integer")
        return cls(max_connections=max_connections, enabled=enabled, enabled_declared=declared)


# Routers that ``routers`` in agentflow.json can switch off. ``websocket`` is the streaming
# endpoint /v1/graph/ws, which can also be switched off through ``websocket.enabled``; both
# spellings are supported and the more restrictive one wins (see ``init_routes``).
TOGGLEABLE_ROUTERS = ("checkpointer", "evals", "media", "store", "websocket")

# Routers that stay mounted whatever the config says: the graph is the product, and /ping is
# how orchestrators decide the process is alive.
ALWAYS_ON_ROUTERS = ("graph", "ping")


@dataclass
class RouterConfig:
    """Which optional routers are mounted, parsed from agentflow.json.

    Example::

        "routers": {
            "evals": false,
            "media": false
        }

    Every router is mounted by default, so an absent block (and every config written before
    this setting existed) keeps the full API. Listing one as ``false`` leaves its routes
    unregistered, which is how a production deployment drops surface it does not use --
    ``evals`` and ``media`` being the usual candidates.

    ``graph`` and ``ping`` are always on; see :data:`TOGGLEABLE_ROUTERS` for the rest.

    ``websocket`` names the streaming endpoint ``/v1/graph/ws``, so it can be switched off
    here or through ``websocket.enabled`` -- whichever spelling you prefer. Setting both is
    fine; the endpoint stays unmounted if either says false. It does not cover
    ``/v1/graph/live``, which already refuses non-live graphs on its own.

    Parsing never fails the boot. An unknown name, an always-on name, a non-boolean value or
    a ``routers`` value that is not an object all log a warning and leave the router mounted.
    The cost of that leniency: a typo such as ``"eval": false`` keeps ``/v1/evals`` serving,
    and the startup log is the only place that says so.
    """

    disabled: frozenset[str] = frozenset()
    # Valid names actually written in the block, whatever their value. Used to tell a
    # written ``true`` apart from the default when two spellings could conflict.
    declared: frozenset[str] = frozenset()

    @classmethod
    def from_dict(cls, data: object) -> "RouterConfig":
        if not isinstance(data, dict):
            logger.warning(
                "routers must be an object mapping router names to booleans, got %s; "
                "keeping every router mounted",
                type(data).__name__,
            )
            return cls()

        disabled: set[str] = set()
        declared: set[str] = set()
        for name, value in data.items():
            if name in ALWAYS_ON_ROUTERS:
                logger.warning("Router '%s' cannot be disabled; ignoring routers.%s", name, name)
                continue
            if name not in TOGGLEABLE_ROUTERS:
                logger.warning(
                    "Unknown router '%s' in routers; ignoring it (valid names: %s)",
                    name,
                    ", ".join(TOGGLEABLE_ROUTERS),
                )
                continue
            try:
                enabled = _parse_bool(value, field=f"routers.{name}")
            except ValueError as exc:
                logger.warning("%s; keeping the router mounted", exc)
                continue
            declared.add(name)
            if not enabled:
                disabled.add(name)

        return cls(disabled=frozenset(disabled), declared=frozenset(declared))

    def is_enabled(self, name: str) -> bool:
        """Whether the router registered under ``name`` should be mounted."""
        return name not in self.disabled


class GraphConfig:
    def __init__(self, path: str = "agentflow.json"):
        with Path(path).open() as f:
            self.data: dict = json.load(f)

        # load .env file
        env_file = self.data.get("env")
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)

    @property
    def graph_path(self) -> str:
        agent = self.data.get("agent")
        if agent:
            return agent

        raise ValueError("Agent graph not found")

    @property
    def checkpointer_path(self) -> str | None:
        return self.data.get("checkpointer", None)

    @property
    def injectq_path(self) -> str | None:
        return self.data.get("injectq", None)

    @property
    def store_path(self) -> str | None:
        return self.data.get("store", None)

    @property
    def redis_url(self) -> str | None:
        return self.data.get("redis", None)

    @property
    def thread_name_generator_path(self) -> str | None:
        return self.data.get("thread_name_generator", None)

    @property
    def observability(self) -> dict | None:
        """The declarative ``observability`` block (Logfire / LangSmith).

        Shape mirrors ``agentflow.runtime.publisher.setup_observability``::

            {
              "level": "standard",
              "logfire":   {"enabled": true, "service_name": "my-agent", ...},
              "langsmith": {"enabled": true, "project": "my-agent", "endpoint": null}
            }

        Secrets (``LOGFIRE_TOKEN``, ``LANGSMITH_API_KEY``) stay in the
        environment and are never read from here.
        """
        return self.data.get("observability", None)

    @property
    def authorization_path(self) -> str | None:
        """
        Get the authorization backend selector from configuration.

        Accepts, in order of precedence:
        - ``"module:attribute"`` -- a custom ``AuthorizationBackend`` to load.
        - a built-in name: ``"ownership"`` (owner-only thread access) or
          ``"allow_all"``/``"default"``/``"none"`` (any authenticated user).
        - ``None`` (not configured) -- defaults by run mode: ``ownership`` in
          production, ``allow_all`` in development.

        Returns:
            str | None: The configured selector, or None to use the mode default.
        """
        return self.data.get("authorization", None)

    def auth_config(self) -> dict | None:
        res = self.data.get("auth", None)
        if not res:
            return None

        if isinstance(res, str) and "jwt" in res:
            # Now check jwt secret and algorithm available in env
            secret = os.environ.get("JWT_SECRET_KEY", None)
            algorithm = os.environ.get("JWT_ALGORITHM", None)
            if not secret or not algorithm:
                raise ValueError(
                    "JWT_SECRET_KEY and JWT_ALGORITHM must be set in environment variables",
                )
            return {
                "method": "jwt",
            }

        if isinstance(res, dict):
            method = res.get("method", None)
            path: str | None = res.get("path", None)
            if not path or not method:
                raise ValueError("Both method and path must be provided in auth config")

            if method == "custom" and path:
                return {
                    "method": "custom",
                    "path": path,
                }

        raise ValueError(f"Unsupported auth method: {res}")

    @property
    def rate_limit(self) -> RateLimitConfig | None:
        """
        Get rate limit configuration from agentflow.json.

        Returns:
            RateLimitConfig if 'rate_limit' key is present and enabled, else None.

        Example agentflow.json entry::

            "rate_limit": {
                "enabled": true,
                "requests": 100,
                "window": 60,
                "by": "ip"
            }
        """
        data = self.data.get("rate_limit", None)
        if data is None:
            return None
        config = RateLimitConfig.from_dict(data)
        if not config.enabled:
            return None
        return config

    @cached_property
    def routers(self) -> "RouterConfig":
        """Which optional routers to mount, from agentflow.json (``routers`` key).

        Returns a config with nothing disabled when the key is absent. Cached because
        parsing warns about bad entries, and the include loop reads this once per router --
        without the cache each warning would be repeated that many times at startup.
        """
        return RouterConfig.from_dict(self.data.get("routers", {}))

    @property
    def websocket(self) -> "WebSocketConfig":
        """WebSocket settings from agentflow.json (``websocket`` key).

        Returns a config with ``enabled=True`` and ``max_connections=None`` (unlimited) when
        the key is absent.
        """
        data = self.data.get("websocket", None)
        if data is None:
            return WebSocketConfig(max_connections=None)
        return WebSocketConfig.from_dict(data)
