"""Unit tests for ThreadOwnershipResolver (L1 LRU + optional Redis L2)."""

from __future__ import annotations

import pytest

from agentflow_cli.src.app.core.auth.ownership_resolver import ThreadOwnershipResolver


class _CountingLookup:
    """Async owner lookup that records how many times it was hit."""

    def __init__(self, owners: dict[str, str]):
        self.owners = owners
        self.calls = 0

    async def __call__(self, thread_id: str):
        self.calls += 1
        return self.owners.get(str(thread_id))


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, bytes] = {}
        self.gets = 0
        self.sets = 0

    async def get(self, key):
        self.gets += 1
        return self.store.get(key)

    async def set(self, key, value):
        self.sets += 1
        self.store[key] = value.encode() if isinstance(value, str) else value

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_resolves_and_caches_owner_in_l1():
    lookup = _CountingLookup({"t1": "alice"})
    r = ThreadOwnershipResolver(lookup)

    assert await r.owner_of("t1") == "alice"
    assert await r.owner_of("t1") == "alice"
    assert await r.owner_of("t1") == "alice"
    # Only the first call hit the backing lookup; the rest were L1 hits.
    assert lookup.calls == 1


@pytest.mark.asyncio
async def test_negative_result_is_never_cached():
    lookup = _CountingLookup({})  # no owners
    r = ThreadOwnershipResolver(lookup)

    assert await r.owner_of("ghost") is None
    assert await r.owner_of("ghost") is None
    # Each miss must re-check: a nonexistent thread can become owned at any moment.
    assert lookup.calls == 2


@pytest.mark.asyncio
async def test_redis_l2_is_populated_and_promotes_to_l1():
    lookup = _CountingLookup({"t1": "alice"})
    redis = _FakeRedis()
    r = ThreadOwnershipResolver(lookup, redis=redis)

    assert await r.owner_of("t1") == "alice"  # DB -> fills L2 + L1
    assert redis.sets == 1

    # A fresh resolver sharing the same Redis resolves without touching the DB.
    lookup2 = _CountingLookup({"t1": "alice"})
    r2 = ThreadOwnershipResolver(lookup2, redis=redis)
    assert await r2.owner_of("t1") == "alice"
    assert lookup2.calls == 0  # served from L2
    # And it is now in r2's L1 too (no further Redis reads).
    gets_before = redis.gets
    assert await r2.owner_of("t1") == "alice"
    assert redis.gets == gets_before


@pytest.mark.asyncio
async def test_evict_clears_l1_and_l2():
    lookup = _CountingLookup({"t1": "alice"})
    redis = _FakeRedis()
    r = ThreadOwnershipResolver(lookup, redis=redis)

    await r.owner_of("t1")
    await r.evict("t1")
    assert not redis.store  # L2 cleared

    await r.owner_of("t1")
    assert lookup.calls == 2  # had to re-resolve after eviction


@pytest.mark.asyncio
async def test_l1_lru_is_bounded():
    lookup = _CountingLookup({f"t{i}": f"u{i}" for i in range(10)})
    r = ThreadOwnershipResolver(lookup, max_size=3)

    for i in range(10):
        await r.owner_of(f"t{i}")

    # Only the 3 most-recent survive in L1; older ones must re-resolve.
    calls_before = lookup.calls
    await r.owner_of("t9")  # recent -> L1 hit
    assert lookup.calls == calls_before
    await r.owner_of("t0")  # evicted -> re-resolve
    assert lookup.calls == calls_before + 1


@pytest.mark.asyncio
async def test_redis_errors_degrade_to_lookup():
    class _BrokenRedis:
        async def get(self, key):
            raise RuntimeError("redis down")

        async def set(self, key, value):
            raise RuntimeError("redis down")

        async def delete(self, key):
            raise RuntimeError("redis down")

    lookup = _CountingLookup({"t1": "alice"})
    r = ThreadOwnershipResolver(lookup, redis=_BrokenRedis())
    # Redis failing must not fail the request; falls through to the DB lookup.
    assert await r.owner_of("t1") == "alice"


@pytest.mark.asyncio
async def test_not_implemented_propagates():
    async def _lookup(thread_id):
        raise NotImplementedError

    r = ThreadOwnershipResolver(_lookup)
    with pytest.raises(NotImplementedError):
        await r.owner_of("t1")
