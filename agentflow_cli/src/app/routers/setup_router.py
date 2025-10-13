from fastapi import FastAPI

from .checkpointer.router import router as checkpointer_router
from .graph import router as graph_router
from .ping.router import router as ping_router
from .store import router as store_router


def init_routes(app: FastAPI):
    """
    Initialize the routes for the FastAPI application.

    This function includes the graph and checkpointer routers for pyagenity functionality.
    Auth and GraphQL routers are disabled for now.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes
        will be added.
    """
    app.include_router(graph_router)
    app.include_router(checkpointer_router)
    app.include_router(store_router)
    app.include_router(ping_router)
