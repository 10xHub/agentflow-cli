import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings


IS_PRODUCTION = False
# TODO: Change the logger name to the appropriate name
LOGGER_NAME = os.getenv("LOGGER_NAME", "pyagenity-api")

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

    APP_NAME: str
    APP_VERSION: str
    MODE: str
    # CRITICAL = 50
    # FATAL = CRITICAL
    # ERROR = 40
    # WARNING = 30
    # WARN = WARNING
    # INFO = 20
    # DEBUG = 10
    # NOTSET = 0
    LOG_LEVEL: int

    SUMMARY: str = "Backend Base"

    #################################
    ###### CORS Config ##############
    #################################
    ORIGINS: str
    ALLOWED_HOST: str

    #################################
    ###### REDIS Config ##########
    #################################
    REDIS_URL: str
    REDIS_HOST: str
    REDIS_PORT: int

    #################################
    ###### sentry Config ############
    #################################
    SENTRY_DSN: str

    # JWT Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str

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
