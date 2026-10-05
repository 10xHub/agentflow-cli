"""Scalable thread-ownership resolution with a two-tier cache.

Thread ownership is *immutable* -- a thread's owner is set when the thread is created and
never changes; only deletion removes it. That makes the owner safe to cache aggressively, so
after the first lookup an authorization check costs nothing (an in-process hit) instead of a
database round-trip per request.

Cache tiers:

- **L1**: a bounded in-process LRU (per worker) with a short TTL.
- **L2** (optional): a shared Redis, so workers/instances do not each re-hit the database.

Deleting a thread evicts it from this worker's L1 and from L2, but another worker's L1 cannot
be reached. A deleted id can be created again by a different user, so a stale L1 entry would
keep granting the old owner access on that worker. The L1 TTL bounds how long that lasts; the
L2 TTL covers an eviction that failed to reach Redis.

Only *positive* results (a known owner) are cached. A ``None`` result (the thread does not
exist yet) is **never** cached: a nonexistent thread can become owned by the very next
request, and a cached ``None`` would let a later caller be treated as the creator of a thread
someone else just made (a time-of-check/time-of-use hole).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable


logger = logging.getLogger("agentflow-cli.authorization")

# Sentinel signalling the backing checkpointer cannot resolve ownership at all
# (``aget_thread_owner`` raised ``NotImplementedError``). Propagated so the caller can
# degrade gracefully instead of treating every thread as unowned.
OwnerLookup = Callable[[str], Awaitable["str | int | None"]]

DEFAULT_L1_TTL_SECONDS = 30.0
DEFAULT_L2_TTL_SECONDS = 3600


class ThreadOwnershipResolver:
    """Resolve (and cache) the owning ``user_id`` for a ``thread_id``.

    Args:
        lookup: async ``(thread_id) -> user_id | None`` backing lookup (typically
            ``checkpointer.aget_thread_owner``). May raise ``NotImplementedError`` if the
            checkpointer cannot resolve ownership; that propagates uncached.
        redis: optional async Redis-like client (``get``/``set``/``delete`` coroutines).
            When absent the resolver is L1-only. Redis errors degrade to the DB lookup and
            never fail a request.
        max_size: L1 LRU capacity (entries).
        redis_prefix: key namespace for L2 entries.
        l1_ttl: seconds an L1 entry is trusted; bounds staleness after a delete elsewhere.
        l2_ttl: seconds an L2 entry lives in Redis.
    """

    def __init__(
        self,
        lookup: OwnerLookup,
        *,
        redis: object | None = None,
        max_size: int = 10_000,
        redis_prefix: str = "af:authz:owner",
        l1_ttl: float = DEFAULT_L1_TTL_SECONDS,
        l2_ttl: int = DEFAULT_L2_TTL_SECONDS,
    ) -> None:
        self._lookup = lookup
        self._redis = redis
        self._max_size = max(1, max_size)
        self._prefix = redis_prefix
        self._l1_ttl = l1_ttl
        self._l2_ttl = l2_ttl
        # key -> (owner, monotonic expiry)
        self._l1: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ public

    async def owner_of(self, thread_id: str | int) -> str | None:
        """Return the owning ``user_id`` for ``thread_id``, or None if it has no owner.

        Raises:
            NotImplementedError: if the backing checkpointer cannot resolve ownership.
        """
        key = str(thread_id)

        cached = await self._l1_get(key)
        if cached is not None:
            return cached

        from_redis = await self._redis_get(key)
        if from_redis is not None:
            await self._l1_put(key, from_redis)
            return from_redis

        owner = await self._lookup(key)  # may raise NotImplementedError -> propagate
        if owner is None:
            return None  # never cache negatives (TOCTOU on new threads)

        owner_str = str(owner)
        await self._l1_put(key, owner_str)
        await self._redis_set(key, owner_str)
        return owner_str

    async def evict(self, thread_id: str | int) -> None:
        """Drop any cached owner for ``thread_id`` (call when a thread is deleted)."""
        key = str(thread_id)
        async with self._lock:
            self._l1.pop(key, None)
        await self._redis_delete(key)

    # ------------------------------------------------------------------ L1

    async def _l1_get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._l1.get(key)
            if entry is None:
                return None
            owner, expires_at = entry
            if time.monotonic() >= expires_at:
                del self._l1[key]
                return None
            self._l1.move_to_end(key)  # mark most-recently-used
            return owner

    async def _l1_put(self, key: str, owner: str) -> None:
        async with self._lock:
            self._l1[key] = (owner, time.monotonic() + self._l1_ttl)
            self._l1.move_to_end(key)
            while len(self._l1) > self._max_size:
                self._l1.popitem(last=False)  # evict least-recently-used

    # ------------------------------------------------------------------ L2 (Redis)

    def _redis_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def _redis_get(self, key: str) -> str | None:
        if self._redis is None:
            return None
        try:
            value = await self._redis.get(self._redis_key(key))  # type: ignore[attr-defined]
        except Exception as exc:  # degrade to DB; never fail the request
            logger.debug("Ownership L2 get failed for %s: %s", key, exc)
            return None
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes | bytearray) else str(value)

    async def _redis_set(self, key: str, owner: str) -> None:
        if self._redis is None:
            return
        try:
            # evict() removes the entry on delete; the TTL covers an eviction that failed.
            await self._redis.set(  # type: ignore[attr-defined]
                self._redis_key(key), owner, ex=self._l2_ttl
            )
        except Exception as exc:
            logger.debug("Ownership L2 set failed for %s: %s", key, exc)

    async def _redis_delete(self, key: str) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._redis_key(key))  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("Ownership L2 delete failed for %s: %s", key, exc)
