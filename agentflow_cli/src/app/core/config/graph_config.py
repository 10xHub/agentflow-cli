import ipaddress
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator


logger = logging.getLogger("agentflow_api")


def _empty_parameters() -> dict[str, Any]:
    return {"type": "object", "properties": {}, "required": []}


class RemoteToolConfig(BaseModel):
    """Trusted model-facing schema for a tool executed by the client."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    node_name: str = Field(alias="node", min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=_empty_parameters)

    @field_validator("node_name", "name", "description")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("parameters")
    @classmethod
    def _validate_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        parameters = dict(value)
        parameters.setdefault("type", "object")
        parameters.setdefault("properties", {})
        parameters.setdefault("required", [])
        if parameters["type"] != "object":
            raise ValueError("remote tool parameters.type must be 'object'")
        if not isinstance(parameters["properties"], dict):
            raise ValueError("remote tool parameters.properties must be an object")
        if not isinstance(parameters["required"], list) or not all(
            isinstance(item, str) for item in parameters["required"]
        ):
            raise ValueError("remote tool parameters.required must be a list of strings")
        return parameters

    def to_tool_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_REMOTE_TOOLS_ADAPTER = TypeAdapter(list[RemoteToolConfig])


def validate_remote_tools(raw: object) -> list[RemoteToolConfig]:
    """Validate remote-tool declarations for both CLI audit and API startup."""
    if not isinstance(raw, list):
        raise ValueError("remote_tools must be a list")

    try:
        tools = _REMOTE_TOOLS_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid remote_tools configuration: {exc}") from exc

    seen: set[str] = set()
    for tool in tools:
        if tool.name in seen:
            raise ValueError(f"Duplicate remote tool name '{tool.name}'")
        seen.add(tool.name)
    return tools


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


def _parse_networks(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list | tuple):
        raise ValueError("rate_limit.trusted_proxies must be a list of IPs or CIDR ranges")
    networks = []
    for item in raw:
        try:
            networks.append(str(ipaddress.ip_network(str(item).strip(), strict=False)))
        except ValueError as exc:
            raise ValueError(f"rate_limit.trusted_proxies: invalid network {item!r}") from exc
    return tuple(networks)


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
            "exclude_paths": ["/ping", "/docs", "/redoc", "/openapi.json"]
        }

    Example (Redis backend)::

        "rate_limit": {
            "enabled": true,
            "backend": "redis",
            "requests": 100,
            "window": 60,
            "by": "ip",
            "trusted_proxy_headers": true,
            "exclude_paths": ["/ping"],
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
    # Networks your proxies connect from. When set, X-Forwarded-For is honoured only for
    # requests whose peer address is in one of them, so a client that reaches the app
    # directly (bypassing the proxy) cannot pick its own address.
    trusted_proxies: tuple[str, ...] = ()

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
        trusted_proxies = _parse_networks(data.get("trusted_proxies", []))

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
            trusted_proxies=trusted_proxies,
        )


# Finite defaults so an unconfigured server cannot be held open by one client.
DEFAULT_WS_MAX_CONNECTIONS = 1000
DEFAULT_WS_MAX_CONNECTIONS_PER_USER = 10


@dataclass
class WebSocketConfig:
    """WebSocket connection limits parsed from agentflow.json.

    Example::

        "websocket": {
            "max_connections": 1000,
            "max_connections_per_user": 10,
            "realtime_models": ["gemini-2.5-flash-live"]
        }

    ``max_connections`` caps the concurrent WebSocket connections this server *process*
    accepts (realtime ``/v1/graph/live`` + streaming ``/v1/graph/ws``).
    ``max_connections_per_user`` caps how many of those one verified user may hold, so a
    single account cannot take every slot. Both are per process, like the in-memory
    rate-limit backend; size them per worker.

    A missing key gets a finite default (1000 and 10). Set a key to ``0`` or ``null`` to make
    it unlimited. WebSocket handshakes, and every graph run started over ``/v1/graph/ws``, also
    count against the global ``rate_limit`` bucket shared with REST requests.

    ``realtime_models`` lists the models a ``/v1/graph/live`` client may ask for in its init
    frame. Any other requested model is ignored and the agent's own model is used. Empty (the
    default) means clients cannot choose the model.
    """

    max_connections: int | None
    max_connections_per_user: int | None = DEFAULT_WS_MAX_CONNECTIONS_PER_USER
    realtime_models: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "WebSocketConfig":
        if not isinstance(data, dict):
            raise ValueError("websocket must be an object")
        return cls(
            max_connections=_connection_limit(data, "max_connections", DEFAULT_WS_MAX_CONNECTIONS),
            max_connections_per_user=_connection_limit(
                data, "max_connections_per_user", DEFAULT_WS_MAX_CONNECTIONS_PER_USER
            ),
            realtime_models=_string_list(data, "realtime_models"),
        )


def _string_list(data: dict, key: str) -> tuple[str, ...]:
    raw = data.get(key)
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"websocket.{key} must be a list of strings")
    return tuple(item.strip() for item in raw if item.strip())


def _connection_limit(data: dict, key: str, default: int) -> int | None:
    """A missing key gets ``default``; an explicit ``0`` or ``null`` means unlimited."""
    if key not in data:
        return default
    raw = data[key]
    if raw in (None, 0):
        return None
    value = int(raw)
    if value < 0:
        raise ValueError(f"websocket.{key} must be a non-negative integer")
    return value


@dataclass
class AgUiConfig:
    """AG-UI protocol endpoint settings parsed from agentflow.json.

    Example::

        "ag_ui": {
            "enabled": true,
            "allow_client_tools": true
        }

    When enabled, ``POST /v1/ag-ui`` streams the graph as AG-UI events, so AG-UI clients
    such as CopilotKit can use the agent. It needs the ``ag-ui`` extra
    (``pip install "10xscale-agentflow-cli[ag-ui]"``). Off unless explicitly enabled.

    ``allow_client_tools`` (default ``true``) offers the tools an AG-UI client sends with each
    run to the model for that run. They run in the caller's own browser, cannot take the name of
    a server tool, and must pass size limits. Set it to ``false`` to accept only the client tools
    declared under ``remote_tools``.
    """

    enabled: bool = False
    allow_client_tools: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AgUiConfig":
        if not isinstance(data, dict):
            raise ValueError("ag_ui must be an object")
        return cls(
            enabled=_parse_bool(data.get("enabled", False), field="ag_ui.enabled"),
            allow_client_tools=_parse_bool(
                data.get("allow_client_tools", True), field="ag_ui.allow_client_tools"
            ),
        )


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
    def remote_tools(self) -> list[RemoteToolConfig]:
        """Validated client-executed tool schemas configured at startup."""
        return validate_remote_tools(self.data.get("remote_tools", []))

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

    @property
    def websocket(self) -> "WebSocketConfig":
        """WebSocket connection limits from agentflow.json (``websocket`` key).

        Returns the default limits when the key is absent.
        """
        data = self.data.get("websocket", None)
        return WebSocketConfig.from_dict({} if data is None else data)

    @property
    def ag_ui(self) -> AgUiConfig:
        """AG-UI endpoint settings from agentflow.json (``ag_ui`` key).

        Returns a disabled config when the key is absent.
        """
        data = self.data.get("ag_ui", None)
        return AgUiConfig.from_dict({} if data is None else data)
