import asyncio
import logging
import time
from collections import deque

from .base import BaseRateLimitBackend, RateLimitDecision


logger = logging.getLogger("agentflow_api.rate_limit")

_NUM_STRIPES = 64


class MemoryRateLimitBackend(BaseRateLimitBackend):
    """In-process sliding-window rate limiter.

    This is useful for development and single-process deployments. It is not
    shared across workers or containers; use Redis for distributed enforcement.
    """

    _SWEEP_INTERVAL = 2000

    def __init__(self, max_unique_keys: int = 50_000) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._last_seen: dict[str, float] = {}
        self._locks = [asyncio.Lock() for _ in range(_NUM_STRIPES)]
        self._sweep_lock = asyncio.Lock()
        self._bg_tasks: set[asyncio.Task] = set()
        self._check_count = 0
        self._max_unique_keys = max_unique_keys

    def _stripe_lock(self, key: str) -> asyncio.Lock:
        return self._locks[hash(key) % _NUM_STRIPES]

    def _schedule_sweep(self, window: int) -> None:
        task = asyncio.ensure_future(self._sweep(window))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    def _evict_oldest_bucket(self) -> None:
        if not self._last_seen:
            return
        oldest_key = min(self._last_seen, key=self._last_seen.__getitem__)
        self._buckets.pop(oldest_key, None)
        self._last_seen.pop(oldest_key, None)

    async def _sweep(self, window: int) -> None:
        async with self._sweep_lock:
            cutoff = time.monotonic() - window * 2
            stale = [k for k, ts in self._last_seen.items() if ts < cutoff]
            for key in stale:
                self._buckets.pop(key, None)
                self._last_seen.pop(key, None)
            if stale:
                logger.debug("Rate-limit memory sweep removed %d stale buckets", len(stale))

    async def check(self, key: str, *, limit: int, window: int) -> RateLimitDecision:
        now = time.monotonic()
        window_start = now - window

        self._check_count += 1
        if self._check_count % self._SWEEP_INTERVAL == 0:
            self._schedule_sweep(window)

        async with self._stripe_lock(key):
            if key not in self._buckets and len(self._buckets) >= self._max_unique_keys:
                logger.warning(
                    "Rate-limit bucket cap (%d) reached; running emergency sweep",
                    self._max_unique_keys,
                )
                await self._sweep(window)
                if len(self._buckets) >= self._max_unique_keys:
                    self._evict_oldest_bucket()

            bucket = self._buckets.setdefault(key, deque())
            self._last_seen[key] = now

            while bucket and bucket[0] < window_start:
                bucket.popleft()

            count = len(bucket)
            if count >= limit:
                reset_after = max(1, int(bucket[0] + window - now) + 1)
                return RateLimitDecision(allowed=False, remaining=0, reset_after=reset_after)

            bucket.append(now)
            return RateLimitDecision(
                allowed=True,
                remaining=limit - len(bucket),
                reset_after=window,
            )

    async def close(self) -> None:
        for task in self._bg_tasks:
            task.cancel()
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()
