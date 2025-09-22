from fastapi import Depends

from pyagenity_api.src.app.core import Settings, get_settings, logger


def init_sentry(settings: Settings = Depends(get_settings)):
    """
    Initializes Sentry for error tracking and performance monitoring.

    This function sets up Sentry with the provided settings, including DSN and integrations
    for FastAPI and Starlette. It also configures the sample rates for traces and profiles.

    Args:
        settings (Settings, optional): The application settings containing Sentry configuration.
            Defaults to the result of `Depends(get_settings)`.

    Returns:
        None
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes=[403, range(500, 599)],
                ),
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes=[403, range(500, 599)],
                ),
            ],
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
        )
        logger.debug("Sentry initialized")
    except ImportError:
        logger.warning("sentry_sdk is not installed, Please install it to use Sentry")
    except Exception as e:
        logger.warning(f"Error initializing Sentry: {e}")
