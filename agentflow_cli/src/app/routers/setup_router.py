from fastapi import FastAPI

from .checkpointer.router import router as checkpointer_router
from .evals import router as evals_router
from .graph import router as graph_router
from .media.router import router as media_router
from .ping.router import router as ping_router
from .store import router as store_router


def init_routes(app: FastAPI, *, evals: bool = True):
    """
    Initialize the routes for the FastAPI application.

    This function includes the graph and checkpointer routers for agentflow functionality.
    Auth and GraphQL routers are disabled for now.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes
        will be added.
        evals (bool): Mount the evals report viewer. It has no auth, so production
        leaves it out.
    """
    app.include_router(graph_router)
    app.include_router(checkpointer_router)
    app.include_router(store_router)
    if evals:
        app.include_router(evals_router)
    app.include_router(ping_router)
    app.include_router(media_router)
