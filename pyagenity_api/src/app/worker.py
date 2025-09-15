# import os

# from fastapi_injector import attach_injector_taskiq
# from redis.asyncio import Redis
# from snowflakekit import SnowflakeConfig, SnowflakeGenerator
# from taskiq import (
#     InMemoryBroker,
#     SimpleRetryMiddleware,
#     TaskiqEvents,
#     TaskiqState,
# )
# from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
# from tortoise import Tortoise

# from src.app.core import get_settings, logger
# from src.app.core.config.worker_middleware import MonitoringMiddleware
# from src.app.db import TORTOISE_ORM
# from src.tests import register_fake_repos


# env = os.environ.get("ENVIRONMENT")
# _IS_TEST = env and env == "pytest"

# settings = get_settings()

# redis_async_result = RedisAsyncResultBackend(
#     redis_url=settings.REDIS_URL,
# )

# # Or you can use PubSubBroker if you need broadcasting
# broker = ListQueueBroker(
#     url=settings.REDIS_URL,
#     queue_name=f"{settings.APP_NAME}-queue",
# ).with_result_backend(redis_async_result)
# broker.add_middlewares(
#     [
#         MonitoringMiddleware(),
#         SimpleRetryMiddleware(default_retry_count=3),
#         # PrometheusMiddleware(server_addr="0.0.0.0", server_port=9000),
#     ]
# )

# # this is for testing
# if _IS_TEST:
#     broker = InMemoryBroker()

# redis_client = Redis(
#     host=settings.REDIS_HOST,
#     port=settings.REDIS_PORT,
#     # password=settings.REDIS_PASSWORD,
#     # db=settings.REDIS_DB,
# )

# # Setup id generator
# config = SnowflakeConfig(
#     epoch=settings.SNOWFLAKE_EPOCH,
#     node_id=settings.SNOWFLAKE_NODE_ID,
#     worker_id=settings.SNOWFLAKE_WORKER_ID,
#     time_bits=settings.SNOWFLAKE_TIME_BITS,
#     node_bits=settings.SNOWFLAKE_NODE_BITS,
#     worker_bits=settings.SNOWFLAKE_WORKER_BITS,
# )

# # setup injection
# injector = Injector()
# attach_injector_taskiq(broker.state, injector=injector)
# if _IS_TEST:
#     register_fake_repos(injector)

# # save into injector
# injector.binder.bind(SnowflakeGenerator, SnowflakeGenerator(config=config))
# injector.binder.bind(Redis, redis_client)


# @broker.on_event(TaskiqEvents.WORKER_STARTUP)
# async def startup(state: TaskiqState) -> None:
#     if _IS_TEST:
#         return
#     await redis_client.ping()
#     logger.info("Got redis connection")
#     # setup database
#     await Tortoise.init(config=TORTOISE_ORM)


# @broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
# async def shutdown(state: TaskiqState) -> None:
#     if _IS_TEST:
#         return
#     # Here we close our pool on shutdown event.
#     state.redis.disconnect()
#     await Tortoise.close_connections()
