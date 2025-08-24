# from contextlib import asynccontextmanager

import os

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import ORJSONResponse
from fastapi_injector import attach_injector
from injector import Injector
from pyagenity.checkpointer import BaseCheckpointer
from pyagenity.graph import CompiledGraph
from pyagenity.store import BaseStore
from redis.asyncio import Redis
from snowflakekit import SnowflakeConfig, SnowflakeGenerator

# from tortoise import Tortoise
from src.app.core import get_settings, init_errors_handler, init_logger, setup_middleware
from src.app.core.config.graph_config import GraphConfig
from src.app.loader import load_checkpointer, load_graph, load_store
from src.app.routers import init_routes


settings = get_settings()
# redis_client = Redis(
#     host=settings.REDIS_HOST,
#     port=settings.REDIS_PORT,
# )

graph_path = os.environ.get("GRAPH_PATH", "pyagenity.json")
graph_config = GraphConfig(graph_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the cache
    # RedisCacheBackend(settings.REDIS_URL)
    graph = await load_graph(graph_config.graph_path)
    # save injector
    injector.binder.bind(CompiledGraph, graph)

    # load checkpointer
    checkpointer = load_checkpointer(graph_config.checkpointer_path)
    injector.binder.bind(BaseCheckpointer, checkpointer)

    # load Store
    store = load_store(graph_config.store_path)
    injector.binder.bind(BaseStore, store)

    yield
    # Clean up
    # await close_caches()
    # close all the connections


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

injector = Injector()
attach_injector(app, injector=injector)

init_logger(settings.LOG_LEVEL)

# init error handler
init_errors_handler(app)

# init routes
init_routes(app)

config = SnowflakeConfig(
    epoch=settings.SNOWFLAKE_EPOCH,
    node_id=settings.SNOWFLAKE_NODE_ID,
    worker_id=settings.SNOWFLAKE_WORKER_ID,
    time_bits=settings.SNOWFLAKE_TIME_BITS,
    node_bits=settings.SNOWFLAKE_NODE_BITS,
    worker_bits=settings.SNOWFLAKE_WORKER_BITS,
)

injector.binder.bind(
    SnowflakeGenerator,
    SnowflakeGenerator(config=config),
)
# injector.binder.bind(Redis, redis_client)
