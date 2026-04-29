# Rate Limit Review

Reviewed files:

- `agentflow-api/agentflow_cli/src/app/core/config/graph_config.py`
- `agentflow-api/agentflow_cli/src/app/core/middleware/rate_limit.py`
- `agentflow-api/agentflow_cli/src/app/core/config/setup_middleware.py`
- `agentflow-api/agentflow.json`

## Verdict

The current rate limiter is fine as a local development toy, but it is not a production-scalable rate limiter. It uses per-process memory, accepts spoofable client identity by default, serializes every request through one lock, has no backend abstraction, and exposes config that looks production-ready while silently breaking across workers or containers.

For a framework whose promise is "focus on building the agent, not the scalable logic," this needs a backend-driven design.

## Findings

### High: limits are per process, not per deployment

`RateLimitMiddleware` stores buckets in `self._buckets`, an in-memory dictionary owned by one Python process:

- `rate_limit.py:44-46`
- `rate_limit.py:73-89`

That means every Uvicorn/Gunicorn worker has its own quota. If the config says `100 requests / 60s` and the API runs with 8 workers, the real limit can become roughly `800 requests / 60s` per host. If the app runs across 5 containers, it can become roughly `4000 requests / 60s`.

This is the main scalability failure.

### High: the API config has no backend choice

`RateLimitConfig` only supports:

- `enabled`
- `requests`
- `window`
- `by`

See `graph_config.py:9-32`. The example config in `agentflow.json:6-11` also has no way to say whether the limiter should use memory, Redis, or another storage backend.

That makes the current implementation a hard-coded memory strategy wearing a production config costume.

### High: `X-Forwarded-For` is trusted unconditionally

The IP key uses `X-Forwarded-For` whenever present:

- `rate_limit.py:55-59`

This is dangerous unless the app is guaranteed to sit behind a trusted proxy that strips untrusted forwarding headers. A direct client can spoof `X-Forwarded-For` and rotate the value to bypass per-IP limits.

This should be configurable and tied to trusted proxy settings, or use Starlette/Uvicorn proxy header handling in a controlled deployment path.

### Medium: one global lock serializes all limiter checks

Every request enters the same `asyncio.Lock`:

- `rate_limit.py:46`
- `rate_limit.py:73`

Even unrelated IPs block each other. Under load, the rate limiter becomes a request funnel. This is especially awkward because rate limiting is supposed to protect the app during pressure, not become the pressure point.

### Medium: bucket cleanup is passive and memory can grow

Old timestamps are only removed when the same bucket key is seen again:

- `rate_limit.py:76-78`

If many unique client keys appear once, their empty or stale buckets can remain in `_buckets` indefinitely. A hostile client can generate many spoofed `X-Forwarded-For` values and inflate memory.

### Medium: `global` mode is global only inside one process

The `global` bucket key is `__global__`:

- `rate_limit.py:52-54`

Because storage is local memory, this is not actually global across workers, pods, hosts, or deployments. The name promises more than the implementation can deliver.

### Medium: algorithm choice is fixed and storage-heavy

The middleware implements a sliding window by storing every request timestamp in a deque:

- `rate_limit.py:44`
- `rate_limit.py:88`

This gives accurate sliding windows, but memory grows with `number_of_keys * requests`. Redis can support this with sorted sets, but for high traffic a token bucket or fixed-window-with-Lua approach may be cheaper and easier to operate.

### Medium: `X-RateLimit-Reset` is not a standard reset timestamp

The response uses seconds-until-reset as `X-RateLimit-Reset`:

- `rate_limit.py:130`
- `rate_limit.py:137`

Many clients expect reset to be an epoch timestamp. If the project wants delta seconds, use a clearer header such as `X-RateLimit-Reset-After`, or document the behavior explicitly.

### Low: config validation is too narrow for future extension

`RateLimitConfig.from_dict` validates `by`, `requests`, and `window`, but there is no namespacing for backend-specific settings:

- `graph_config.py:19-32`

If Redis is added by sprinkling `redis_url` into the same flat object, the config will become messy quickly.

### Low: no route/method exclusions

The limiter applies to every HTTP request once enabled:

- `setup_middleware.py:151-155`

That includes docs, health checks, metrics, readiness probes, and possibly streaming endpoints. Production deployments usually need `exclude_paths`, `include_paths`, or route groups.


Claude Sonnet built the rate limiter equivalent of putting a bicycle lock on a cloud load balancer.

It has the aesthetic of scalability: config file, middleware class, headers, neat docstring. But the actual quota lives in a Python dictionary inside one worker. The moment you add another worker, container, or node, the "limit" becomes a polite suggestion with multiplication enabled.

The `global` option is especially funny. It is global in the same way a sticky note on one laptop is company policy. Accurate within a very small emotional radius.

And trusting `X-Forwarded-For` directly is the security version of accepting "I am definitely the CEO" because someone wrote it in a request header.

To be fair, this is a reasonable first draft for local demos. But for AgentFlow's stated goal, this should not be the production shape.

## Proposed config shape

Add one more keyword: `backend`.

Recommended default:

```json
{
  "rate_limit": {
    "enabled": true,
    "backend": "memory",
    "requests": 100,
    "window": 60,
    "by": "ip"
  }
}
```

Production Redis example:

```json
{
  "rate_limit": {
    "enabled": true,
    "backend": "redis",
    "redis": {
      "url": "${REDIS_URL}",
      "prefix": "agentflow:rate-limit"
    },
    "requests": 100,
    "window": 60,
    "by": "ip"
  }
}
```

Future custom backend example:

```json
{
  "rate_limit": {
    "enabled": true,
    "backend": "custom",
    "path": "my_project.rate_limit:backend",
    "requests": 100,
    "window": 60,
    "by": "user"
  }
}
```

Suggested fields:

| Field | Type | Notes |
| --- | --- | --- |
| `enabled` | bool | Enables/disables middleware. |
| `backend` | string | `memory`, `redis`, or `custom`. Default can be `memory` for backward compatibility. |
| `requests` | int | Max requests per window. |
| `window` | int | Window duration in seconds. |
| `by` | string | Start with `ip` and `global`; later add `user`, `api_key`, `thread`, or `custom`. |
| `redis.url` | string | Required when `backend = "redis"` unless a shared app Redis config is used. |
| `redis.prefix` | string | Key prefix for isolation. |
| `exclude_paths` | list[string] | Optional health/docs/metrics exclusions. |
| `trusted_proxy_headers` | bool | Only honor forwarding headers when explicitly enabled. |

## Proposed architecture

Split the rate limiter into three layers:

1. `RateLimitConfig`
   Parses and validates config, including backend-specific options.

2. `RateLimitBackend`
   Owns the storage and algorithm.

3. `RateLimitMiddleware`
   Extracts identity, asks the backend whether the request is allowed, and writes response headers.

Example interface:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_after: int


class RateLimitBackend(Protocol):
    async def check(self, key: str, *, limit: int, window: int) -> RateLimitDecision:
        ...
```

Then implement:

- `MemoryRateLimitBackend`
- `RedisRateLimitBackend`
- `CustomRateLimitBackend`

The middleware should not know whether the counter lives in a deque, Redis, Postgres, or a user's custom implementation.

## Redis backend recommendation

For Redis, use an atomic operation. Do not perform `GET`, calculate in Python, then `SET`, because concurrent requests will race.

Two good options:

1. Fixed window with Redis `INCR` + `EXPIRE`
   Simple, fast, atomic enough if wrapped carefully. Less smooth at window boundaries.

2. Sliding window with Redis sorted sets + Lua script
   More accurate, more expensive, still atomic if implemented in Lua.

For AgentFlow, I would start with fixed window or token bucket unless exact sliding-window semantics are required. The framework likely cares more about predictable distributed enforcement than perfect boundary smoothing.

## Migration plan

### Step 1: Make config extensible

Update `RateLimitConfig` to include:

- `backend: str = "memory"`
- `redis_url: str | None = None`
- `redis_prefix: str = "agentflow:rate-limit"`
- `exclude_paths: tuple[str, ...] = ()`
- `trusted_proxy_headers: bool = False`

Keep current config working by defaulting `backend` to `memory`.

### Step 2: Extract the backend interface

Move the deque logic out of `RateLimitMiddleware` into `MemoryRateLimitBackend`.

This keeps the current behavior intact while creating the seam for Redis.

### Step 3: Add Redis backend

Use `redis.asyncio` from the existing optional `redis` dependency.

The Redis backend should:

- use a configurable key prefix
- use atomic commands or Lua
- return the same `RateLimitDecision` as memory
- fail closed or fail open based on an explicit config option, not accidental exception behavior

### Step 4: Fix identity extraction

Add an identity resolver with explicit modes:

- `global`
- `ip`
- later: `user`, `api_key`, `custom`

Only trust `X-Forwarded-For` when configured. Otherwise use `request.client.host`.

### Step 5: Add exclusions

Support paths like:

```json
"exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json"]
```

This avoids rate limiting health checks and operational endpoints.

### Step 6: Add tests

Minimum tests:

- config parses old format without `backend`
- config parses `backend = "memory"`
- config parses `backend = "redis"` and requires Redis URL
- invalid backend raises a helpful error
- memory backend enforces limit
- Redis backend enforces limit across two backend instances
- `X-Forwarded-For` is ignored unless trusted proxy mode is enabled
- excluded paths bypass limiter

## Recommended next implementation target

Do this in one focused PR:

1. Add `backend` parsing with backward compatibility.
2. Extract `MemoryRateLimitBackend`.
3. Keep current runtime behavior unchanged when `backend` is omitted.
4. Add tests for config and memory behavior.

Then a second PR can add Redis without mixing architectural cleanup and networked storage in the same change.

