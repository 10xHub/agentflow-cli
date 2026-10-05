"""Tests for RoleBasedAuthorizationBackend (roles -> scopes) and config wiring."""

from __future__ import annotations

import pytest

from agentflow_cli.src.app.core.auth.authorization import (
    RoleBasedAuthorizationBackend,
    all_scopes,
)


ROLES = {
    "admin": ["*"],
    "member": ["graph:invoke", "graph:stream", "checkpointer:read"],
    "viewer": ["checkpointer:read"],
}


def _backend(**kw):
    return RoleBasedAuthorizationBackend(ROLES, default_scopes=["graph:read"], **kw)


def test_member_gets_role_scopes_plus_defaults():
    b = _backend()
    scopes = b.scopes_for({"user_id": "u1", "roles": ["member"]})
    assert "graph:invoke" in scopes
    assert "checkpointer:read" in scopes
    assert "graph:read" in scopes  # default
    assert "checkpointer:delete" not in scopes


def test_admin_wildcard_expands_to_all_scopes():
    b = _backend()
    assert set(b.scopes_for({"role": "admin"})) == set(all_scopes())


def _required_scopes() -> set[str]:
    """Every ``resource:action`` a route asks ``RequirePermission`` for."""
    from agentflow_cli.src.app.core.auth.permissions import RequirePermission
    from agentflow_cli.src.app.routers.checkpointer.router import router as checkpointer
    from agentflow_cli.src.app.routers.graph.router import router as graph
    from agentflow_cli.src.app.routers.media.router import router as media
    from agentflow_cli.src.app.routers.store.router import router as store

    found: set[str] = set()

    def walk(dependant):
        for dep in dependant.dependencies:
            if isinstance(dep.call, RequirePermission):
                found.add(f"{dep.call.resource}:{dep.call.action}")
            walk(dep)

    for router in (checkpointer, graph, media, store):
        for route in router.routes:
            walk(route.dependant)
    return found


def test_wildcard_role_reaches_every_route():
    required = _required_scopes()
    assert {"store:read", "store:write", "store:delete"} <= required
    assert required <= all_scopes()


def test_no_role_gets_only_defaults():
    b = _backend()
    assert b.scopes_for({"user_id": "u1"}) == ["graph:read"]


def test_multiple_roles_union():
    b = _backend()
    scopes = b.scopes_for({"roles": ["viewer", "member"]})
    assert "graph:invoke" in scopes and "checkpointer:read" in scopes


def test_single_role_string_accepted():
    b = _backend()
    assert "checkpointer:read" in b.scopes_for({"role": "viewer"})


def test_isolation_defaults_to_owner_and_is_configurable():
    assert _backend().isolation_scope() == "owner"
    assert _backend(isolation="none").isolation_scope() == "none"
    assert _backend(isolation="bogus").isolation_scope() == "owner"  # invalid -> owner


@pytest.mark.asyncio
async def test_rbac_still_enforces_thread_ownership():
    """RBAC inherits owner-only object isolation from OwnershipAuthorizationBackend."""

    class _Cp:
        async def aget_thread_owner(self, thread_id):
            return "alice" if str(thread_id) == "t1" else None

    b = RoleBasedAuthorizationBackend(ROLES, checkpointer=_Cp())
    assert await b.authorize({"user_id": "alice"}, "checkpointer", "read", resource_id="t1") is True
    assert await b.authorize({"user_id": "bob"}, "checkpointer", "read", resource_id="t1") is False


def test_loader_builds_rbac_from_dict_config():
    from agentflow_cli.src.app.loader import _resolve_authorization_backend

    b = _resolve_authorization_backend(
        {"backend": "rbac", "roles": ROLES, "default_scopes": ["graph:read"]}
    )
    assert isinstance(b, RoleBasedAuthorizationBackend)
    assert "graph:invoke" in b.scopes_for({"roles": ["member"]})


def test_loader_rejects_unknown_backend_dict():
    from agentflow_cli.src.app.loader import _resolve_authorization_backend

    with pytest.raises(ValueError):
        _resolve_authorization_backend({"backend": "nope"})
