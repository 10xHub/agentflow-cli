import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings


IS_PRODUCTION = False
LOGGER_NAME = os.getenv("LOGGER_NAME", "agentflow-cli")

logger = logging.getLogger(LOGGER_NAME)


class Settings(BaseSettings):
    """
    This class defines the configuration settings for the application.

    Attributes:
        APP_NAME (str): The name of the application.
        APP_VERSION (str): The version of the application.
        MODE (str): The mode in which the application is running (e.g., development, production).
        LOG_LEVEL (int): The logging level for the application.
        SUMMARY (str): A brief summary of the application. Default is "Backend Base".

        ORIGINS (str): CORS allowed origins.
        ALLOWED_HOST (str): CORS allowed hosts.
        REDIS_URL (str): The URL for the Redis server.

        SENTRY_DSN (str): The DSN for Sentry error tracking.

    Config:
        extra (str): Configuration for handling extra fields. Default is "allow".
    """

    APP_NAME: str = "MyApp"
    APP_VERSION: str = "0.1.0"
    MODE: str = "development"
    # CRITICAL = 50
    # FATAL = CRITICAL
    # ERROR = 40
    # WARNING = 30
    # WARN = WARNING
    # INFO = 20
    # DEBUG = 10
    # NOTSET = 0
    LOG_LEVEL: str = "INFO"
    IS_DEBUG: bool = True

    SUMMARY: str = "Pyagenity Backend"

    #################################
    ###### CORS Config ##############
    #################################
    ORIGINS: str = "*"
    ALLOWED_HOST: str = "*"

    #################################
    ###### REDIS Config ##########
    #################################
    REDIS_URL: str | None = None

    #################################
    ###### sentry Config ############
    #################################
    SENTRY_DSN: str | None = None

    #################################
    ###### Auth ############
    #################################
    SNOWFLAKE_EPOCH: int = 1609459200000
    SNOWFLAKE_NODE_ID: int = 1
    SNOWFLAKE_WORKER_ID: int = 2
    SNOWFLAKE_TIME_BITS: int = 39
    SNOWFLAKE_NODE_BITS: int = 5
    SNOWFLAKE_WORKER_BITS: int = 8

    class Config:
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    """
    Retrieve and return the application settings.
    If not in production, load settings from a specific environment file.
    Returns:
        Settings: An instance of the Settings class containing
        application configurations.
    """
    logger.info("Loading settings from environment variables and .env if present")
    return Settings()  # type: ignore
