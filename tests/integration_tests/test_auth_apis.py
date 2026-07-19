"""Auth enforcement on protected routes.

With auth enabled, a request that carries no identity must be refused -- the endpoints
are guarded by the real ``RequirePermission`` dependency, not by hand-rolled checks.
"""

from __future__ import annotations

from agentflow_cli.src.app.routers.checkpointer.router import router as checkpointer_router

from .conftest import build_app, make_client, user_headers


HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


def test_request_without_identity_is_rejected():
    app = build_app(routers=[checkpointer_router])
    client = make_client(app)

    r = client.get("/v1/threads/t1/state")  # no X-Test-User header
    assert r.status_code == HTTP_UNAUTHORIZED


def test_request_with_identity_is_authenticated():
    app = build_app(routers=[checkpointer_router])
    client = make_client(app)

    r = client.get("/v1/threads/t1/state", headers=user_headers("alice"))
    assert r.status_code == HTTP_OK
