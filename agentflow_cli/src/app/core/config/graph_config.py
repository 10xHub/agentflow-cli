import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
    by: str  # "ip" | "global"
    backend: str  # "memory" | "redis" | "custom"
    redis_url: str | None
    redis_prefix: str
    exclude_paths: tuple[str, ...]
    trusted_proxy_headers: bool  # honour X-Forwarded-For only when True
    fail_open: bool  # on backend error: True=allow, False=deny

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

        # Validation
        if by not in ("ip", "global"):
            raise ValueError(f"rate_limit.by must be 'ip' or 'global', got '{by}'")
        if backend not in ("memory", "redis", "custom"):
            raise ValueError(
                f"rate_limit.backend must be 'memory', 'redis', or 'custom', got '{backend}'"
            )
        if requests <= 0:
            raise ValueError("rate_limit.requests must be a positive integer")
        if window <= 0:
            raise ValueError("rate_limit.window must be a positive integer")

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
            fail_open=fail_open,
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
    def authorization_path(self) -> str | None:
        """
        Get the authorization backend path from configuration.

        Returns:
            str | None: Path to authorization backend module in format 'module:attribute',
                       or None if not configured
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
