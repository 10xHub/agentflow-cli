from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi_injector import attach_injector
from injector import Injector
from redis.asyncio import Redis
from snowflakeid import SnowflakeIDConfig, SnowflakeIDGenerator
from tortoise import Tortoise

from src.app.core import get_settings, init_errors_handler, init_logger, setup_middleware
from src.app.db import setup_db
from src.app.routers import init_routes


settings = get_settings()
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the cache
    # RedisCacheBackend(settings.REDIS_URL)
    yield
    # Clean up
    # await close_caches()
    # close all the connections
    await Tortoise.close_connections()


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

setup_db(app)

injector = Injector()
attach_injector(app, injector=injector)

init_logger(settings.LOG_LEVEL)

# init error handler
init_errors_handler(app)

# init routes
init_routes(app)

config = SnowflakeIDConfig(
    epoch=1609459200000,
    node_id=1,
    worker_id=1,
    time_bits=39,
    node_bits=5,
    worker_bits=8,
)

injector.binder.bind(SnowflakeIDGenerator, SnowflakeIDGenerator(config=config))
injector.binder.bind(Redis, redis_client)
