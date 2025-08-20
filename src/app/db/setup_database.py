from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from src.app.core import get_settings, logger
from src.app.db.tables.user_constants import USER_TABLES


TORTOISE_ORM = {
    "connections": {
        "master": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": get_settings().POSTGRES_HOST,
                "port": get_settings().POSTGRES_PORT,
                "user": get_settings().POSTGRES_USER,
                "password": get_settings().POSTGRES_PASSWORD,
                "database": get_settings().POSTGRES_DB,
                # choose schema
                "schema": "cv",
                # Minimum connection pool size
                "minsize": 1,
                # Maximum connection pool size
                "maxsize": 5,
                # Connection timeout
                "max_inactive_connection_lifetime": 300,
                # Maximum number of queries before reconnecting
                "max_queries": 50000,
            },
        },
    },  # postgresql
    # "connections": {"default": "mysql://root:123456@127.0.0.1:3306/test"},
    # "connections": {"default": "sqlite://:memory:"},
    # "connections": {"default": "sqlite://./podcast.db"},
    "routers": ["src.app.db.router.Router"],
    "apps": {
        "tables": {
            "models": [*USER_TABLES, "aerich.models"],
            "default_connection": "master",
        },
    },
}


def setup_db(app: FastAPI):
    """
    Set up the database for the FastAPI application using Tortoise ORM.

    This function initializes the Tortoise ORM with the given FastAPI application.
    It registers the Tortoise ORM with the application using the provided configuration.

    Args:
        app (FastAPI): The FastAPI application instance to set up the database for.

    Returns:
        None
    """
    # init tortoise orm
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=False,
        add_exception_handlers=False,
    )

    logger.info("Database setup complete")
