import logging
import sys

from fastapi.logger import logger as fastapi_logger


def init_logger(level: int | str = logging.INFO) -> None:
    """
    Initializes and configures logging for the application.

    This function sets up various loggers used in the application, including
    those for Gunicorn, Uvicorn, FastAPI, database clients, Tortoise ORM, and
    custom loggers. It also configures a console handler to output logs to
    stdout.

    Args:
        level (int): The logging level to set for the loggers.
    """
    # GCLOUD SETUP
    # client = Client()
    # client.get_default_handler()
    # client.setup_logging()

    # setup logging
    gunicorn_error_logger = logging.getLogger("gunicorn.error")
    # gunicorn_logger = logging.getLogger("gunicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = gunicorn_error_logger.handlers
    fastapi_logger.handlers = gunicorn_error_logger.handlers
    fastapi_logger.setLevel(level)

    # will print debug sql
    logger_db_client = logging.getLogger("db_client")
    logger_db_client.setLevel(level)
    logger_db_client.addHandler(fastapi_logger)

    logger_tortoise = logging.getLogger("tortoise")
    logger_tortoise.setLevel(level)
    logger_tortoise.addHandler(fastapi_logger)

    # register custom logger here
    injector_logging = logging.getLogger("injector")
    injector_logging.setLevel(level)
    injector_logging.addHandler(fastapi_logger)

    # Register custom logger for coding
    # TODO: Change the logger name to the appropriate name
    backend_logging = logging.getLogger("BACKEND_BASE")
    backend_logging.setLevel(level)
    backend_logging.addHandler(fastapi_logger)

    # Package logger
    package_logger = logging.getLogger("PACKAGE")
    package_logger.setLevel(level)
    package_logger.addHandler(fastapi_logger)

    # Create console handler and set level to DEBUG
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    # Add formatter to console handler
    console_handler.setFormatter(formatter)
    # Add console handler to logger
    fastapi_logger.addHandler(console_handler)
