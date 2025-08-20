from fastapi import FastAPI

from src.app.routers.graph import router as graph_router


# from src.app.routers.auth import router as auth_router
# from src.app.routers.graphql import graphql_app


def init_routes(app: FastAPI):
    """
    Initialize the routes for the FastAPI application.

    This function includes the graph router for pyagenity functionality.
    Auth and GraphQL routers are disabled for now.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes
        will be added.
    """
    app.include_router(graph_router)
    # app.include_router(auth_router)
    # app.include_router(graphql_app, prefix="/gql")
