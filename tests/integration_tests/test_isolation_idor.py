"""Cross-user (IDOR) negative tests for the fixes in the production-readiness audit.

Each test drives the REAL request path -- real ``RequirePermission``, real auth
backend, real service -- and asserts that user B cannot reach user A's data.
"""

from __future__ import annotations

import pytest
from agentflow.storage.checkpointer import InMemoryCheckpointer

from agentflow_cli.src.app.routers.checkpointer.router import router as checkpointer_router
from agentflow_cli.src.app.routers.media import MediaService
from agentflow_cli.src.app.routers.media.router import router as media_router

from .conftest import OwnershipAuthz, build_app, make_client, user_headers


HTTP_OK = 200
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_UNSUPPORTED_MEDIA = 415


# ---------------------------------------------------------------------------
# Media ownership (B1: files had no owner; any authenticated caller could read one)
# ---------------------------------------------------------------------------


@pytest.fixture
def media_app(memory_media_settings):
    service = MediaService(settings=memory_media_settings)
    app = build_app(
        routers=[media_router],
        extra_bindings={MediaService: service},
    )
    return app


def test_owner_can_read_own_file_but_other_user_cannot(media_app):
    client = make_client(media_app)

    upload = client.post(
        "/v1/files/upload",
        files={"file": ("a.txt", b"secret-A", "text/plain")},
        headers=user_headers("alice"),
    )
    assert upload.status_code == HTTP_OK, upload.text
    file_id = upload.json()["data"]["file_id"]

    # Owner reads it back.
    owner_get = client.get(f"/v1/files/{file_id}", headers=user_headers("alice"))
    assert owner_get.status_code == HTTP_OK
    assert owner_get.content == b"secret-A"

    # A different authenticated user must NOT be able to read, inspect, or get a URL
    # for it -- and must get 404 (not 403), so the id's existence is not confirmed.
    for path in (f"/v1/files/{file_id}", f"/v1/files/{file_id}/info", f"/v1/files/{file_id}/url"):
        resp = client.get(path, headers=user_headers("mallory"))
        assert resp.status_code == HTTP_NOT_FOUND, f"{path} -> {resp.status_code}"


def test_upload_rejects_disallowed_content_type(monkeypatch, memory_media_settings):
    # Restrict the allowlist to images; a text upload must be refused (H1 hardening).
    memory_media_settings.MEDIA_ALLOWED_CONTENT_TYPES = "image/*"
    monkeypatch.setattr(
        "agentflow_cli.src.app.routers.media.router.get_media_settings",
        lambda: memory_media_settings,
    )
    service = MediaService(settings=memory_media_settings)
    app = build_app(routers=[media_router], extra_bindings={MediaService: service})
    client = make_client(app)

    resp = client.post(
        "/v1/files/upload",
        files={"file": ("a.txt", b"hello", "text/plain")},
        headers=user_headers("alice"),
    )
    assert resp.status_code == HTTP_UNSUPPORTED_MEDIA


def test_upload_over_size_cap_is_rejected(monkeypatch, memory_media_settings):
    # Tiny cap so the streaming size-guard trips without allocating anything large.
    memory_media_settings.MEDIA_MAX_SIZE_MB = 0.001  # ~1 KB
    monkeypatch.setattr(
        "agentflow_cli.src.app.routers.media.router.get_media_settings",
        lambda: memory_media_settings,
    )
    service = MediaService(settings=memory_media_settings)
    app = build_app(routers=[media_router], extra_bindings={MediaService: service})
    client = make_client(app)

    resp = client.post(
        "/v1/files/upload",
        files={"file": ("big.txt", b"x" * 5000, "text/plain")},
        headers=user_headers("alice"),
    )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# Authorization backend gets the resource_id (B1 #2) -- path AND body
# ---------------------------------------------------------------------------


def test_authz_blocks_other_user_on_owned_thread_path():
    authz = OwnershipAuthz()
    authz.own("thread-A", "alice")
    app = build_app(
        routers=[checkpointer_router],
        authz=authz,
        checkpointer=InMemoryCheckpointer(),
    )
    client = make_client(app)

    # Owner is allowed through (empty state is fine -- 200 proves authz passed).
    owner = client.get("/v1/threads/thread-A/state", headers=user_headers("alice"))
    assert owner.status_code == HTTP_OK

    # Another user is refused at the authorization layer.
    other = client.get("/v1/threads/thread-A/messages", headers=user_headers("mallory"))
    assert other.status_code == HTTP_FORBIDDEN
    # The authz backend actually received the thread id it needed to make the call.
    assert "thread-A" in [str(r) for r in authz.seen_resource_ids]


def test_authz_receives_thread_id_from_request_body():
    """Regression for B1 #2: invoke/stream/stop/fix carry thread_id in the BODY.

    Before the fix, ``resource_id`` came only from path params, so a body-carried
    thread_id never reached the authz backend for exactly the endpoints that execute
    and mutate. This drives a minimal body-carrying route through the real
    ``RequirePermission`` and asserts the backend now sees it.
    """
    from typing import Any

    from fastapi import APIRouter, Depends

    from agentflow_cli.src.app.core.auth.permissions import RequirePermission

    probe = APIRouter()

    @probe.post("/v1/graph/stop")
    async def _stop(
        payload: dict,
        user: dict[str, Any] = Depends(RequirePermission("graph", "stop")),
    ):
        return {"ok": True}

    authz = OwnershipAuthz()
    authz.own("thread-A", "alice")
    app = build_app(routers=[probe], authz=authz)
    client = make_client(app)

    # Owner allowed; body thread_id must reach authz.
    owner = client.post(
        "/v1/graph/stop", json={"thread_id": "thread-A"}, headers=user_headers("alice")
    )
    assert owner.status_code == HTTP_OK
    assert "thread-A" in [str(r) for r in authz.seen_resource_ids]

    # Different user is blocked -- proving body-derived resource_id is enforced.
    other = client.post(
        "/v1/graph/stop", json={"thread_id": "thread-A"}, headers=user_headers("mallory")
    )
    assert other.status_code == HTTP_FORBIDDEN


# ---------------------------------------------------------------------------
# Built-in ownership backend wired end-to-end (the secure production default)
# ---------------------------------------------------------------------------


class _OwnerRegistryCheckpointer:
    """Minimal checkpointer exposing global thread-owner resolution."""

    def __init__(self) -> None:
        self.owners: dict[str, str] = {}
        self.owner_lookups = 0

    def own(self, thread_id: str, user_id: str) -> None:
        self.owners[thread_id] = user_id

    async def aget_thread_owner(self, thread_id):
        self.owner_lookups += 1
        return self.owners.get(str(thread_id))


def test_ownership_backend_enforces_owner_only_reads():
    from agentflow_cli.src.app.core.auth.authorization import OwnershipAuthorizationBackend

    registry = _OwnerRegistryCheckpointer()
    registry.own("thread-A", "alice")
    authz = OwnershipAuthorizationBackend(checkpointer=registry)
    # The service reads through a real in-memory checkpointer; authz resolves ownership
    # through the registry above.
    app = build_app(routers=[checkpointer_router], authz=authz, checkpointer=InMemoryCheckpointer())
    client = make_client(app)

    # Owner reads their thread.
    assert (
        client.get("/v1/threads/thread-A/state", headers=user_headers("alice")).status_code
        == HTTP_OK
    )
    # Non-owner is refused object-level access with no custom code -- built-in backend.
    assert (
        client.get("/v1/threads/thread-A/messages", headers=user_headers("mallory")).status_code
        == HTTP_FORBIDDEN
    )


def test_ownership_backend_blocks_invoke_and_stream_on_foreign_thread():
    """Regression for the reported gap: running (invoke/stream) another user's thread
    must be rejected *before* the graph executes, not just at write time."""
    from typing import Any

    from fastapi import APIRouter, Depends

    from agentflow_cli.src.app.core.auth.authorization import OwnershipAuthorizationBackend
    from agentflow_cli.src.app.core.auth.permissions import RequirePermission

    graph_probe = APIRouter()

    @graph_probe.post("/v1/graph/invoke")
    async def _invoke(
        payload: dict,
        user: dict[str, Any] = Depends(RequirePermission("graph", "invoke")),
    ):
        return {"ran": True}

    @graph_probe.post("/v1/graph/stream")
    async def _stream(
        payload: dict,
        user: dict[str, Any] = Depends(RequirePermission("graph", "stream")),
    ):
        return {"ran": True}

    registry = _OwnerRegistryCheckpointer()
    registry.own("thread-A", "alice")
    authz = OwnershipAuthorizationBackend(checkpointer=registry)
    app = build_app(routers=[graph_probe], authz=authz, checkpointer=InMemoryCheckpointer())
    client = make_client(app)

    # Owner can run their own thread.
    assert (
        client.post(
            "/v1/graph/invoke", json={"thread_id": "thread-A"}, headers=user_headers("alice")
        ).status_code
        == HTTP_OK
    )
    # Attacker cannot invoke or stream someone else's thread -- blocked up front.
    assert (
        client.post(
            "/v1/graph/invoke", json={"thread_id": "thread-A"}, headers=user_headers("mallory")
        ).status_code
        == HTTP_FORBIDDEN
    )
    assert (
        client.post(
            "/v1/graph/stream", json={"thread_id": "thread-A"}, headers=user_headers("mallory")
        ).status_code
        == HTTP_FORBIDDEN
    )
    # A brand-new thread for the attacker is fine (their own new session).
    assert (
        client.post(
            "/v1/graph/invoke", json={"thread_id": "new-one"}, headers=user_headers("mallory")
        ).status_code
        == HTTP_OK
    )


def test_ownership_is_cached_across_requests():
    """End-to-end scalability guarantee: repeated requests for the same thread cost a
    single owner lookup, not one per request."""
    from agentflow_cli.src.app.core.auth.authorization import OwnershipAuthorizationBackend

    registry = _OwnerRegistryCheckpointer()
    registry.own("thread-A", "alice")
    authz = OwnershipAuthorizationBackend(checkpointer=registry)
    app = build_app(routers=[checkpointer_router], authz=authz, checkpointer=InMemoryCheckpointer())
    client = make_client(app)

    for _ in range(6):
        client.get("/v1/threads/thread-A/state", headers=user_headers("alice"))
        client.get("/v1/threads/thread-A/messages", headers=user_headers("mallory"))

    # 12 HTTP requests touched thread-A; ownership was resolved from the backing
    # store exactly once (everything else served from the in-process cache).
    assert registry.owner_lookups == 1
