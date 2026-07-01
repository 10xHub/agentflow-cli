import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from injectq import InjectQ
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from agentflow_cli.src.app.core.middleware.rate_limit import RateLimitMiddleware, build_backend
from agentflow_cli.src.app.core.middleware.request_limits import RequestSizeLimitMiddleware
from agentflow_cli.src.app.core.middleware.security_headers import SecurityHeadersMiddleware

from .graph_config import GraphConfig
from .sentry_config import init_sentry
from .settings import get_settings, logger


# Paths that should be excluded from GZip compression (streaming endpoints)
GZIP_EXCLUDED_PATHS = frozenset({"/v1/graph/stream"})


class SelectiveGZipMiddleware:
    """
    GZip middleware that excludes certain paths from compression.

    This is necessary because streaming endpoints need to send data
    immediately without buffering, but GZipMiddleware buffers the
    entire response before compressing.
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 1000):
        self.app = app
        self.gzip_app = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] in GZIP_EXCLUDED_PATHS:
            # Skip GZip for excluded paths - pass through directly
            await self.app(scope, receive, send)
        else:
            # Apply GZip for all other paths
            await self.gzip_app(scope, receive, send)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID and timestamp to each request and response.

    This middleware generates a unique request ID and a timestamp when a request is received.
    It adds these values to the request state and includes them in the response headers.


    Methods:
        dispatch(request: Request, call_next):
            Generates a unique request ID and timestamp, adds them to the request state,
            and includes them in the response headers.

    Returns:
        Response: The HTTP response with added request ID and timestamp headers.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Middleware dispatch method to handle incoming requests.

        This method generates a unique request ID and a timestamp for each incoming request,
        adds them to the request state, and includes them in the response headers for
        logging purposes.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable): The next middleware or route handler to be called.

        Returns:
            Response: The HTTP response with added headers for request ID and timestamp.
        """
        # Generate request ID and timestamp
        request_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Add request ID and timestamp to request headers
        request.state.request_id = request_id
        request.state.timestamp = timestamp
        logger.debug(f"Requesting: Request ID: {request_id}, Timestamp: {timestamp}")

        # Proceed with the request
        response = await call_next(request)

        # Add request ID and timestamp to response headers for logging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Timestamp"] = timestamp
        logger.debug(f"Response: Request ID: {request_id}, Timestamp: {timestamp}")

        return response


def _attach_otel_publisher(container: InjectQ, settings) -> None:
    """Wire OtelPublisher into the container when OTEL_ENABLED=true.

    Merges with any publisher already bound in the container:
      - None bound         → bind OtelPublisher directly
      - CompositePublisher → add OtelPublisher to it
      - Single publisher   → wrap both in a new CompositePublisher
    """
    try:
        from agentflow.runtime.publisher.base_publisher import BasePublisher
        from agentflow.runtime.publisher.composite_publisher import CompositePublisher
        from agentflow.runtime.publisher.otel_publisher import ObservabilityLevel, OtelPublisher
    except ImportError:
        logger.warning(
            "OTEL_ENABLED=true but opentelemetry packages are not installed. "
            "Install with: pip install '10xscale-agentflow[otel]'"
        )
        return

    try:
        level = ObservabilityLevel(settings.OTEL_LEVEL.lower())
    except ValueError:
        logger.warning(
            "Invalid OTEL_LEVEL=%r, falling back to 'standard'. Valid: spans, standard, full",
            settings.OTEL_LEVEL,
        )
        level = ObservabilityLevel.STANDARD

    otel_publisher = OtelPublisher(level=level)
    existing = container.try_get(BasePublisher)

    if existing is None:
        container.bind_instance(BasePublisher, otel_publisher)
        logger.info("OTEL: OtelPublisher bound (level=%s)", level)
    elif isinstance(existing, CompositePublisher):
        existing.add_publisher(otel_publisher)
        logger.info("OTEL: OtelPublisher added to existing CompositePublisher (level=%s)", level)
    else:
        container.bind_instance(BasePublisher, CompositePublisher([existing, otel_publisher]))
        logger.info(
            "OTEL: wrapped %s + OtelPublisher in CompositePublisher (level=%s)",
            type(existing).__name__,
            level,
        )


def _setup_observability(container: InjectQ | None, graph_config: GraphConfig | None) -> None:
    """Wire Logfire/LangSmith from the ``observability`` block of ``agentflow.json``.

    Configures the tracer provider(s)/exporters and binds an ``OtelPublisher``
    into the DI container. This runs at app-construction time, before the graph
    is loaded and compiled — the only reliable attach point, because InjectQ
    freezes the ``BasePublisher`` binding at ``container.compile()`` (which runs
    inside ``StateGraph.compile()``). The core ``StateGraph.compile()`` guard
    preserves a publisher already present in the container instead of clobbering
    it with ``None``.

    Secrets stay in the environment (``LOGFIRE_TOKEN``, ``LANGSMITH_API_KEY``);
    only non-secret settings live in ``agentflow.json``.
    """
    if container is None or graph_config is None:
        return

    obs_cfg = graph_config.observability
    if not obs_cfg:
        return

    logfire_on = bool((obs_cfg.get("logfire") or {}).get("enabled", False))
    langsmith_on = bool((obs_cfg.get("langsmith") or {}).get("enabled", False))
    if not logfire_on and not langsmith_on:
        return

    try:
        from agentflow.runtime.publisher.base_publisher import BasePublisher
        from agentflow.runtime.publisher.composite_publisher import CompositePublisher
        from agentflow.runtime.publisher.exporters import setup_observability
        from agentflow.runtime.publisher.otel_publisher import ObservabilityLevel, OtelPublisher
    except ImportError:
        logger.warning(
            "observability is configured but required packages are not installed. "
            "Install with: pip install '10xscale-agentflow[observability]'"
        )
        return

    # Configure the provider(s)/exporter(s) only. graph=None means no publisher
    # is attached here; we bind it into the container ourselves below so it is
    # in place before the graph compiles.
    try:
        setup_observability(None, obs_cfg)
    except (ImportError, ValueError) as exc:
        logger.warning("Observability setup skipped: %s", exc)
        return

    try:
        level = ObservabilityLevel(str(obs_cfg.get("level", "standard")).lower())
    except ValueError:
        logger.warning(
            "Invalid observability level=%r, falling back to 'standard'.",
            obs_cfg.get("level"),
        )
        level = ObservabilityLevel.STANDARD

    otel_publisher = OtelPublisher(level=level)
    existing = container.try_get(BasePublisher)

    if existing is None:
        container.bind_instance(BasePublisher, otel_publisher)
    elif isinstance(existing, CompositePublisher):
        existing.add_publisher(otel_publisher)
    else:
        container.bind_instance(BasePublisher, CompositePublisher([existing, otel_publisher]))

    logger.info(
        "Observability enabled (logfire=%s, langsmith=%s, level=%s)",
        logfire_on,
        langsmith_on,
        level,
    )


def _setup_otel(app: FastAPI, settings) -> None:
    """Configure OpenTelemetry tracing and instrument the FastAPI app.

    Reads OTEL_EXPORTER_OTLP_ENDPOINT from settings. If unset, falls back to
    the standard OTEL_EXPORTER_OTLP_ENDPOINT env var (honoured automatically
    by the OTLP exporter). A ConsoleSpanExporter is used when no endpoint is
    configured and the app is not in production, so traces are visible locally
    without any collector.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OTEL_ENABLED=true but opentelemetry packages are not installed. "
            "Install with: pip install '10xscale-agentflow-cli[otel]'"
        )
        return

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            logger.info("OTEL: exporting traces to %s", endpoint)
        except ImportError:
            logger.warning(
                "OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry-exporter-otlp "
                "is not installed. Install with: pip install '10xscale-agentflow-cli[otel]'"
            )
            return
    else:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTEL: no endpoint configured, printing spans to console")

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    logger.info("OTEL: FastAPI instrumentation active (service=%s)", settings.OTEL_SERVICE_NAME)


def setup_middleware(
    app: FastAPI,
    graph_config: GraphConfig | None = None,
    container: InjectQ | None = None,
):
    """
    Set up middleware for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
        graph_config (GraphConfig | None): Optional graph configuration used to
            enable dynamic rate limiting from ``agentflow.json``.

    Middleware:
        - CORS: Configured based on settings.ORIGINS.
        - TrustedHost: Configured with allowed hosts from settings.ALLOWED_HOST.
        - GZip: Applied with a minimum size of 1000 bytes (excludes streaming endpoints).
        - RateLimit: Applied when ``rate_limit`` is configured in ``agentflow.json``.
    """
    settings = get_settings()

    if settings.OTEL_ENABLED:
        _setup_otel(app, settings)
        if container is not None:
            _attach_otel_publisher(container, settings)

    # Declarative Logfire/LangSmith wiring from agentflow.json (before compile).
    _setup_observability(container, graph_config)
    # init cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOST.split(","))

    # Add request size limit middleware (protects against DoS via large payloads)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.MAX_REQUEST_SIZE)

    # Add security headers middleware (if enabled)
    if settings.SECURITY_HEADERS_ENABLED:
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_hsts=settings.HSTS_ENABLED,
            hsts_max_age=settings.HSTS_MAX_AGE,
            hsts_include_subdomains=settings.HSTS_INCLUDE_SUBDOMAINS,
            hsts_preload=settings.HSTS_PRELOAD,
            frame_options=settings.FRAME_OPTIONS,
            content_type_options=settings.CONTENT_TYPE_OPTIONS,
            xss_protection=settings.XSS_PROTECTION,
            referrer_policy=settings.REFERRER_POLICY,
            permissions_policy=settings.PERMISSIONS_POLICY,
            csp_policy=settings.CSP_POLICY,
        )

    app.add_middleware(RequestIDMiddleware)

    # Use SelectiveGZipMiddleware to exclude streaming endpoints from compression
    # Streaming endpoints need immediate data transmission without buffering
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)

    # Apply rate limiting only when configured in agentflow.json
    if graph_config is not None:
        rate_limit_config = graph_config.rate_limit
        if rate_limit_config is not None:
            backend = build_backend(rate_limit_config, container=container)
            # Store on app.state so lifespan can close it cleanly
            app.state.rate_limit_backend = backend
            app.add_middleware(
                RateLimitMiddleware,
                config=rate_limit_config,
                backend=backend,
            )
            logger.info(
                "Rate limiting enabled: backend=%s, %d req/%ds, by=%s, "
                "exclude_paths=%s, trusted_proxy_headers=%s",
                rate_limit_config.backend,
                rate_limit_config.requests,
                rate_limit_config.window,
                rate_limit_config.by,
                rate_limit_config.exclude_paths or "(none)",
                rate_limit_config.trusted_proxy_headers,
            )

    logger.debug("Middleware set up")

    # Initialize Sentry
    init_sentry(settings)
