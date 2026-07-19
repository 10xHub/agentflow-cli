"""Tests for the boot-time route-protection invariant."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Depends, FastAPI

from agentflow_cli.src.app.core.auth.permissions import RequirePermission
from agentflow_cli.src.app.core.auth.route_guard import (
    assert_all_routes_protected,
    find_unprotected_routes,
)


def _protected_app() -> FastAPI:
    app = FastAPI()

    @app.get("/v1/threads/{thread_id}/state")
    async def _state(
        thread_id: str,
        user: dict[str, Any] = Depends(RequirePermission("checkpointer", "read")),
    ):
        return {}

    @app.get("/ping")
    async def _ping():
        return {"data": "pong"}

    return app


def _leaky_app() -> FastAPI:
    app = FastAPI()

    @app.get("/v1/threads/{thread_id}/state")
    async def _state(
        thread_id: str,
        user: dict[str, Any] = Depends(RequirePermission("checkpointer", "read")),
    ):
        return {}

    @app.get("/v1/secret")  # <-- forgot RequirePermission
    async def _secret():
        return {"top": "secret"}

    return app


def test_protected_app_passes():
    app = _protected_app()
    assert find_unprotected_routes(app) == []
    assert_all_routes_protected(app)  # does not raise


def test_leaky_route_is_detected_and_blocks_boot():
    app = _leaky_app()
    unprotected = find_unprotected_routes(app)
    assert any("/v1/secret" in u for u in unprotected)
    with pytest.raises(RuntimeError) as exc:
        assert_all_routes_protected(app)
    assert "/v1/secret" in str(exc.value)


def test_public_allowlist_exempts_path():
    app = _leaky_app()
    # Explicitly declaring /v1/secret public makes the invariant pass.
    assert_all_routes_protected(app, public_paths=frozenset({"/ping", "/v1/secret"}))


def test_real_app_has_no_unprotected_routes():
    import agentflow_cli.src.app.main as main_module

    assert find_unprotected_routes(main_module.app) == []
