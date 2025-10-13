from typing import TYPE_CHECKING

from fastapi import Depends

from agentflow_cli.src.app.core import Settings, get_settings, logger


if TYPE_CHECKING:  # pragma: no cover - only for type hints
    import sentry_sdk  # noqa: F401
    from sentry_sdk.integrations.fastapi import FastApiIntegration  # noqa: F401
    from sentry_sdk.integrations.starlette import StarletteIntegration  # noqa: F401


def init_sentry(settings: Settings = Depends(get_settings)) -> None:
    """Initialize Sentry for error tracking and performance monitoring.

    The initialization is best-effort: if ``sentry_sdk`` isn't installed or any
    unexpected error occurs, the application continues to run and a warning is
    logged instead of failing hard.
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
        logger.warning("sentry_sdk not installed; install 'agentflow-cli[sentry]' to enable Sentry")
    except Exception as exc:  # intentionally broad: init must not crash app
        logger.warning("Error initializing Sentry: %s", exc)
