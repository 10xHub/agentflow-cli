from fastapi import APIRouter, FastAPI

from .checkpointer.router import router as checkpointer_router
from .evals import router as evals_router
from .graph import router as graph_router
from .media.router import router as media_router
from .ping.router import router as ping_router
from .store import router as store_router


AG_UI_INSTALL_HINT = 'pip install "10xscale-agentflow-cli[ag-ui]"'


def _import_ag_ui_router() -> APIRouter:
    from .ag_ui import router

    return router


def _ag_ui_router() -> APIRouter:
    """Import the AG-UI router, which needs the optional ``ag-ui-protocol`` package.

    Imported only when ``ag_ui.enabled`` is set, so servers that leave it off never need the
    package installed.
    """
    try:
        return _import_ag_ui_router()
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".")[0] == "ag_ui":
            raise RuntimeError(
                "ag_ui is enabled in agentflow.json but the AG-UI SDK is not installed. "
                f"Install it with: {AG_UI_INSTALL_HINT}"
            ) from exc
        raise


def init_routes(app: FastAPI, *, evals: bool = True, ag_ui: bool = False):
    """
    Initialize the routes for the FastAPI application.

    This function includes the graph and checkpointer routers for agentflow functionality.
    Auth and GraphQL routers are disabled for now.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes
        will be added.
        evals (bool): Mount the evals report viewer. It has no auth, so production
        leaves it out.
        ag_ui (bool): Mount the AG-UI endpoint (``POST /v1/ag-ui``). Off unless
        ``ag_ui.enabled`` is set in agentflow.json.
    """
    app.include_router(graph_router)
    app.include_router(checkpointer_router)
    app.include_router(store_router)
    if evals:
        app.include_router(evals_router)
    if ag_ui:
        app.include_router(_ag_ui_router())
    app.include_router(ping_router)
    app.include_router(media_router)
