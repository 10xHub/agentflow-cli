import logging
import sys

from fastapi.logger import logger as fastapi_logger

from agentflow_cli.src.app.core.utils.log_sanitizer import SanitizingFormatter


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

    # Create console handler and set level to DEBUG
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    base_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    # Wrap with sanitizing formatter to prevent sensitive data in logs
    formatter = SanitizingFormatter(base_formatter)

    # Add formatter to console handler
    console_handler.setFormatter(formatter)
    # Add console handler to logger
    fastapi_logger.addHandler(console_handler)

    # Route application loggers through the same sanitizing console handler.
    # NOTE: addHandler expects a logging.Handler, not a Logger.
    for logger_name in ("db_client", "tortoise", "injector", "BACKEND_BASE", "PACKAGE"):
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(level)
        app_logger.addHandler(console_handler)
