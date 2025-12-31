import logging
import os
from functools import lru_cache

from pydantic import field_validator, model_validator
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

    #################################
    ###### Request Limits ###########
    #################################
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB default

    #################################
    ###### Security Headers #########
    #################################
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year in seconds
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = False
    FRAME_OPTIONS: str = "DENY"  # DENY, SAMEORIGIN, or ALLOW-FROM
    CONTENT_TYPE_OPTIONS: str = "nosniff"
    XSS_PROTECTION: str = "1; mode=block"
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str | None = None  # Uses default if None
    CSP_POLICY: str | None = None  # Uses default if None

    SUMMARY: str = "Pyagenity Backend"

    #################################
    ###### CORS Config ##############
    #################################
    ORIGINS: str = "*"
    ALLOWED_HOST: str = "*"

    #################################
    ###### Paths ####################
    #################################
    ROOT_PATH: str = "/"
    DOCS_PATH: str = "/docs"
    REDOCS_PATH: str = "/redocs"

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

    @field_validator("MODE", mode="before")
    @classmethod
    def normalize_mode(cls, v: str | None) -> str:
        """Normalize MODE to lowercase."""
        return v.lower() if v else "development"

    @field_validator("ORIGINS")
    @classmethod
    def warn_cors_wildcard(cls, v: str) -> str:
        """Warn if CORS is set to wildcard in production."""
        mode = os.environ.get("MODE", "development").lower()
        if v == "*" and mode == "production":
            logger.warning(
                "⚠️  SECURITY WARNING: CORS ORIGINS='*' in production.\n"
                "   This allows any website to make requests to your API.\n"
                "   Set ORIGINS to specific domains (e.g., https://yourdomain.com)"
            )
        return v

    @model_validator(mode="after")
    def check_production_security(self):
        """Check for insecure configurations in production mode."""
        if self.MODE == "production":
            warnings = []

            if self.IS_DEBUG:
                warnings.append(
                    "⚠️  DEBUG mode is enabled in production. "
                    "This may expose sensitive information."
                )

            if self.DOCS_PATH or self.REDOCS_PATH:
                warnings.append(
                    "⚠️  API documentation endpoints are enabled in production. "
                    "Consider disabling DOCS_PATH and REDOCS_PATH."
                )

            if self.ALLOWED_HOST == "*":
                warnings.append(
                    "⚠️  ALLOWED_HOST='*' in production. "
                    "Set to specific hostnames for better security."
                )

            if warnings:
                logger.warning("\n".join(["\n🔒 PRODUCTION SECURITY WARNINGS:"] + warnings))

        return self

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
