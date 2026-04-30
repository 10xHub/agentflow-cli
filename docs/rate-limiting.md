# Rate Limiting

AgentFlow can protect your API with a sliding-window rate limiter configured from
`agentflow.json`. The limiter is disabled until you add a `rate_limit` block.

## Quick Start

For local development or a single-process deployment, use the in-memory backend:

```json
{
  "agent": "graph.react:app",
  "rate_limit": {
    "enabled": true,
    "backend": "memory",
    "requests": 100,
    "window": 60,
    "by": "ip",
    "exclude_paths": ["/health", "/docs", "/redoc", "/openapi.json"]
  }
}
```

This allows each client IP to make `100` requests every `60` seconds.

## Production With Redis

Use Redis when your API runs with multiple workers, containers, or servers.
Redis stores the counters centrally, so the limit is enforced across the whole
deployment.

Redis support is optional. Install AgentFlow with the Redis extra before using
`backend: "redis"`:

```bash
pip install "10xscale-agentflow-cli[redis]"
```

Configure Redis in `agentflow.json`:

```json
{
  "agent": "graph.react:app",
  "rate_limit": {
    "enabled": true,
    "backend": "redis",
    "requests": 1000,
    "window": 60,
    "by": "ip",
    "trusted_proxy_headers": true,
    "exclude_paths": ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
    "redis": {
      "url": "${RATE_LIMIT_REDIS_URL}",
      "prefix": "agentflow:rate-limit"
    },
    "fail_open": true
  }
}
```

Then set the environment variable:

```bash
RATE_LIMIT_REDIS_URL=redis://localhost:6379/0
```

The Redis backend uses an atomic Lua script with sorted sets. That means the
check and the request recording happen as one Redis operation, which prevents
concurrent requests from racing past the configured limit.

## Configuration Reference

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | boolean | `true` | Enables the middleware when the `rate_limit` block exists. |
| `backend` | string | `"memory"` | `memory`, `redis`, or `custom`. |
| `requests` | integer | `100` | Maximum requests allowed in each window. |
| `window` | integer | `60` | Window size in seconds. |
| `by` | string | `"ip"` | Limit by client IP or use `"global"` for one shared quota. |
| `exclude_paths` | string array | `[]` | Paths that bypass rate limiting. |
| `trusted_proxy_headers` | boolean | `false` | Whether to use `X-Forwarded-For` as the client IP. |
| `redis.url` | string | `null` | Redis URL for the Redis backend. Required unless a Redis client is injected. |
| `redis.prefix` | string | `"agentflow:rate-limit"` | Prefix for Redis keys. |
| `fail_open` | boolean | `true` | For Redis errors, allow requests when `true` or deny them when `false`. |

## Identity Modes

Use per-IP limits for most public APIs:

```json
{
  "rate_limit": {
    "requests": 100,
    "window": 60,
    "by": "ip"
  }
}
```

Use a global limit when you want one shared quota for the whole service:

```json
{
  "rate_limit": {
    "requests": 5000,
    "window": 60,
    "by": "global"
  }
}
```

Only enable `trusted_proxy_headers` when your app is behind a trusted proxy or
load balancer that strips untrusted forwarding headers from direct clients.

## Response Headers

Every limited response includes:

| Header | Description |
| --- | --- |
| `X-RateLimit-Limit` | Configured request limit. |
| `X-RateLimit-Remaining` | Requests remaining in the current window. |
| `X-RateLimit-Reset` | Unix timestamp for the current reset estimate. |
| `X-RateLimit-Reset-After` | Seconds until the current reset estimate. |
| `Retry-After` | Present on `429` responses. |

When the limit is exceeded, AgentFlow returns `429 Too Many Requests`:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Limit: 100 per 60s. Retry after 12s.",
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 12
  },
  "metadata": {
    "request_id": "request-id",
    "status": "error"
  }
}
```

## Custom Backend

Use a custom backend when you want to store rate-limit state somewhere else.
Implement `BaseRateLimitBackend`, then bind an instance in InjectQ.

```python
from agentflow_cli.src.app.core.middleware.rate_limit import (
    BaseRateLimitBackend,
    RateLimitDecision,
)


class MyRateLimitBackend(BaseRateLimitBackend):
    async def check(self, key: str, *, limit: int, window: int) -> RateLimitDecision:
        allowed = True
        remaining = limit - 1
        reset_after = window
        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            reset_after=reset_after,
        )

    async def close(self) -> None:
        return None
```

Configure AgentFlow to use the custom backend:

```json
{
  "rate_limit": {
    "enabled": true,
    "backend": "custom",
    "requests": 100,
    "window": 60,
    "by": "ip"
  }
}
```

## Choosing A Backend

Use `memory` for local development, tests, demos, and one-process services.

Use `redis` for production APIs, Gunicorn/Uvicorn deployments with multiple
workers, Docker/Kubernetes deployments, and any setup with more than one API
instance. Redis is not needed for the `memory` or `custom` backends.
