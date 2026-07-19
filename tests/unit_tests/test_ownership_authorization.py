"""Unit tests for OwnershipAuthorizationBackend and mode-based default selection."""

from __future__ import annotations

import pytest

from agentflow_cli.src.app.core.auth.authorization import (
    DefaultAuthorizationBackend,
    OwnershipAuthorizationBackend,
)


class _FakeCheckpointer:
    """Resolves thread ownership globally, like PgCheckpointer.aget_thread_owner."""

    def __init__(self, owners: dict[str, str]):
        self.owners = owners  # thread_id -> owner user_id

    async def aget_thread_owner(self, thread_id):
        return self.owners.get(str(thread_id))


def _backend(owners: dict[str, str]) -> OwnershipAuthorizationBackend:
    return OwnershipAuthorizationBackend(checkpointer=_FakeCheckpointer(owners))


ALICE = {"user_id": "alice"}
MALLORY = {"user_id": "mallory"}


@pytest.mark.asyncio
async def test_unauthenticated_is_denied():
    b = _backend({})
    assert await b.authorize({}, "checkpointer", "read", resource_id="t1") is False


@pytest.mark.asyncio
async def test_non_thread_resource_is_allowed():
    b = _backend({})
    # store scopes itself by user_id; ownership backend does not gate it
    assert await b.authorize(ALICE, "store", "read", resource_id="mem1") is True


@pytest.mark.asyncio
async def test_no_resource_id_is_allowed():
    b = _backend({})
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id=None) is True


@pytest.mark.asyncio
async def test_owner_can_read_own_thread():
    b = _backend({"t1": "alice"})
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id="t1") is True


@pytest.mark.asyncio
async def test_non_owner_cannot_read_thread():
    b = _backend({"t1": "alice"})
    assert await b.authorize(MALLORY, "checkpointer", "read", resource_id="t1") is False


@pytest.mark.asyncio
async def test_non_owner_cannot_delete_or_fix_thread():
    b = _backend({"t1": "alice"})
    assert await b.authorize(MALLORY, "checkpointer", "delete", resource_id="t1") is False
    assert await b.authorize(MALLORY, "graph", "fix", resource_id="t1") is False
    assert await b.authorize(MALLORY, "graph", "stop", resource_id="t1") is False


@pytest.mark.asyncio
async def test_invoke_on_new_thread_is_allowed():
    """A run targeting a thread that does not exist yet is a new session -> allow."""
    b = _backend({})  # no threads exist
    assert await b.authorize(ALICE, "graph", "invoke", resource_id="new-thread") is True
    assert await b.authorize(ALICE, "graph", "stream", resource_id="new-thread") is True


@pytest.mark.asyncio
async def test_invoke_and_stream_on_other_users_thread_are_denied():
    """The core fix: you cannot run (invoke/stream) another user's existing thread."""
    b = _backend({"t1": "alice"})
    assert await b.authorize(MALLORY, "graph", "invoke", resource_id="t1") is False
    assert await b.authorize(MALLORY, "graph", "stream", resource_id="t1") is False


@pytest.mark.asyncio
async def test_owner_can_invoke_and_stream_own_thread():
    b = _backend({"t1": "alice"})
    assert await b.authorize(ALICE, "graph", "invoke", resource_id="t1") is True
    assert await b.authorize(ALICE, "graph", "stream", resource_id="t1") is True


@pytest.mark.asyncio
async def test_read_on_nonexistent_thread_is_allowed_empty():
    # A nonexistent thread has no data to leak; reads pass and return empty/404.
    b = _backend({})
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id="ghost") is True


@pytest.mark.asyncio
async def test_unsupported_checkpointer_allows_with_warning():
    class _NoOwnerSupport:
        async def aget_thread_owner(self, thread_id):
            raise NotImplementedError

    b = OwnershipAuthorizationBackend(checkpointer=_NoOwnerSupport())
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id="t1") is True


@pytest.mark.asyncio
async def test_no_checkpointer_allows_through():
    b = OwnershipAuthorizationBackend(checkpointer=None)
    # Property tries the DI container; in this unit context nothing is bound -> None.
    b._checkpointer = None
    assert b.checkpointer is None
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id="t1") is True


@pytest.mark.asyncio
async def test_resolver_error_fails_closed():
    class _Boom:
        async def aget_thread_owner(self, thread_id):
            raise RuntimeError("db down")

    b = OwnershipAuthorizationBackend(checkpointer=_Boom())
    assert await b.authorize(ALICE, "checkpointer", "read", resource_id="t1") is False


@pytest.mark.asyncio
async def test_repeated_checks_hit_backing_lookup_once():
    """Scalability guarantee: ownership is cached, so N requests for a thread cost one
    DB lookup, not N."""

    class _Counting:
        def __init__(self):
            self.calls = 0

        async def aget_thread_owner(self, thread_id):
            self.calls += 1
            return "alice" if str(thread_id) == "t1" else None

    cp = _Counting()
    b = OwnershipAuthorizationBackend(checkpointer=cp)
    for _ in range(5):
        assert await b.authorize(ALICE, "checkpointer", "read", resource_id="t1") is True
        assert await b.authorize(MALLORY, "graph", "invoke", resource_id="t1") is False
    assert cp.calls == 1  # resolved once, then served from cache


def test_builtin_and_mode_defaults(monkeypatch):
    from agentflow_cli.src.app import loader
    from agentflow_cli.src.app.core.config import settings as settings_mod

    resolve = loader._resolve_authorization_backend

    assert isinstance(resolve("ownership"), OwnershipAuthorizationBackend)
    assert isinstance(resolve("allow_all"), DefaultAuthorizationBackend)
    assert isinstance(resolve("none"), DefaultAuthorizationBackend)
    with pytest.raises(ValueError):
        resolve("bogus")

    class _Mode:
        def __init__(self, mode):
            self.MODE = mode

    monkeypatch.setattr(settings_mod, "get_settings", lambda: _Mode("production"))
    assert isinstance(resolve(None), OwnershipAuthorizationBackend)

    monkeypatch.setattr(settings_mod, "get_settings", lambda: _Mode("development"))
    assert isinstance(resolve(None), DefaultAuthorizationBackend)
