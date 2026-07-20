"""Boot-time invariant: every route must go through the authorization layer.

Authorization is applied per-handler via ``Depends(RequirePermission(...))``, which is
precise (each endpoint declares its own resource/action) but easy to forget on a new
endpoint -- and a forgotten guard ships an open endpoint. This module makes that failure
happen at startup instead: :func:`assert_all_routes_protected` refuses to boot if any
non-public route lacks a ``RequirePermission`` dependency.

It adds zero per-request cost and turns "someone forgot the guard" into a loud deploy-time
error rather than a silent production hole.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

from agentflow_cli.src.app.core.auth.permissions import RequirePermission


logger = logging.getLogger("agentflow-cli.route_guard")

# Paths that are intentionally public (no authorization). Keep this list tiny and explicit.
# Evals is a dev-only report viewer over local files (no user data, not a production surface).
DEFAULT_PUBLIC_PATHS = frozenset(
    {
        "/ping",
        "/v1/evals/runs",
        "/v1/evals/runs/{run_id}",
    }
)


def _has_permission_guard(dependant) -> bool:
    """True if ``RequirePermission`` appears anywhere in the dependant subtree."""
    for dep in getattr(dependant, "dependencies", ()):
        if isinstance(getattr(dep, "call", None), RequirePermission):
            return True
        if _has_permission_guard(dep):
            return True
    return False


def find_unprotected_routes(
    app: FastAPI, public_paths: frozenset[str] = DEFAULT_PUBLIC_PATHS
) -> list[str]:
    """Return ``"METHODS path"`` for every route missing a RequirePermission guard."""
    unprotected: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute | APIWebSocketRoute):
            # Starlette infra routes (docs, openapi.json, redoc) are not APIRoutes.
            continue
        if route.path in public_paths:
            continue
        dependant = getattr(route, "dependant", None)
        if dependant is None or not _has_permission_guard(dependant):
            methods = ",".join(sorted(getattr(route, "methods", None) or ["WS"]))
            unprotected.append(f"{methods} {route.path}")
    return unprotected


def assert_all_routes_protected(
    app: FastAPI, public_paths: frozenset[str] = DEFAULT_PUBLIC_PATHS
) -> None:
    """Refuse to start if any non-public route lacks a RequirePermission guard.

    Raises:
        RuntimeError: listing every unprotected route.
    """
    unprotected = find_unprotected_routes(app, public_paths)
    if unprotected:
        raise RuntimeError(
            "Refusing to start: the following routes are not protected by "
            "RequirePermission. Add the dependency, or add the path to the public "
            "allowlist if it is intentionally open:\n  - " + "\n  - ".join(unprotected)
        )
    logger.debug("Route protection invariant OK (%d routes checked).", len(app.routes))
