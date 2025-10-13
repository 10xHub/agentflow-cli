import os

from agentflow.graph import CompiledGraph
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import ORJSONResponse
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi

# from tortoise import Tortoise
from agentflow_cli.src.app.core import (
    get_settings,
    init_errors_handler,
    init_logger,
    setup_middleware,
)
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.loader import attach_all_modules, load_container
from agentflow_cli.src.app.routers import init_routes


settings = get_settings()
# redis_client = Redis(
#     host=settings.REDIS_HOST,
#     port=settings.REDIS_PORT,
# )

graph_path = os.environ.get("GRAPH_PATH", "agentflow.json")
graph_config = GraphConfig(graph_path)
# Load the container
container: InjectQ = load_container(graph_config.injectq_path) or InjectQ.get_instance()

# Save config instance
container.bind_instance(GraphConfig, graph_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the cache
    # RedisCacheBackend(settings.REDIS_URL)

    graph: CompiledGraph | None = await attach_all_modules(
        graph_config,
        container=container,
    )

    # load Store
    # store = load_store(graph_config.store_path)
    # injector.binder.bind(BaseStore, store)

    yield
    # Clean up
    # await close_caches()
    # close all the connections
    if graph:
        # release all the resources
        await graph.aclose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.MODE == "DEVELOPMENT",
    summary=settings.SUMMARY,
    docs_url="/docs",
    redoc_url="/redocs",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

setup_middleware(app)

# attach_injector(app, injector=injector)
setup_fastapi(container=container, app=app)

init_logger(settings.LOG_LEVEL)

# init error handler
init_errors_handler(app)

# init routes
init_routes(app)
