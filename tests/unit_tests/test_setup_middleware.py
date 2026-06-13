import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.config.setup_middleware import (
    setup_middleware,
    SelectiveGZipMiddleware,
)


HTTP_OK = 200
MIN_REQUEST_ID_LEN = 10


def test_request_id_middleware_adds_headers():
    app = FastAPI()
    setup_middleware(app)

    @app.get("/echo")
    def echo():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/echo")
    assert r.status_code == HTTP_OK
    assert "X-Request-ID" in r.headers
    assert "X-Timestamp" in r.headers
    # Ensure stable format (uuid length 36) and iso-like timestamp
    assert len(r.headers["X-Request-ID"]) >= MIN_REQUEST_ID_LEN
    assert "T" in r.headers["X-Timestamp"]


@pytest.mark.asyncio
async def test_selective_gzip_middleware_excludes():
    from unittest.mock import AsyncMock
    called = []
    async def app(scope, receive, send):
        called.append((scope, receive, send))

    with patch("agentflow_cli.src.app.core.config.setup_middleware.GZipMiddleware") as MockGZipMiddleware:
        mock_gzip_instance = AsyncMock()
        MockGZipMiddleware.return_value = mock_gzip_instance

        middleware = SelectiveGZipMiddleware(app)

        # Test excluded path
        scope = {"type": "http", "path": "/v1/graph/stream"}
        receive = MagicMock()
        send = MagicMock()
        await middleware(scope, receive, send)

        assert len(called) == 1
        assert called[0][0] == scope
        mock_gzip_instance.assert_not_called()

        called.clear()
        mock_gzip_instance.reset_mock()

        # Test non-excluded path
        scope2 = {"type": "http", "path": "/v1/graph/other"}
        await middleware(scope2, receive, send)

        assert len(called) == 0
        mock_gzip_instance.assert_called_once_with(scope2, receive, send)


def test_setup_otel_import_error():
    from agentflow_cli.src.app.core.config.setup_middleware import _setup_otel
    settings = MagicMock()
    settings.OTEL_SERVICE_NAME = "test"
    with patch.dict("sys.modules", {"opentelemetry": None}):
        # setup_middleware should catch ImportError and return without raising
        _setup_otel(MagicMock(), settings)


def test_setup_otel_with_endpoint():
    settings = MagicMock()
    settings.OTEL_ENABLED = True
    settings.OTEL_SERVICE_NAME = "test-service"
    settings.OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"

    mock_trace = MagicMock()
    mock_trace.trace = mock_trace
    mock_trace.__path__ = []
    mock_instrumentor = MagicMock()
    mock_resource = MagicMock()
    mock_provider = MagicMock()
    mock_exporter = MagicMock()
    mock_processor = MagicMock()

    modules = {
        "opentelemetry": mock_trace,
        "opentelemetry.trace": mock_trace,
        "opentelemetry.instrumentation.fastapi": mock_instrumentor,
        "opentelemetry.sdk.resources": mock_resource,
        "opentelemetry.sdk.trace": mock_provider,
        "opentelemetry.sdk.trace.export": mock_processor,
        "opentelemetry.exporter": MagicMock(__path__=[]),
        "opentelemetry.exporter.otlp": MagicMock(__path__=[]),
        "opentelemetry.exporter.otlp.proto": MagicMock(__path__=[]),
        "opentelemetry.exporter.otlp.proto.grpc": MagicMock(__path__=[]),
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": mock_exporter,
    }

    with patch.dict("sys.modules", modules):
        mock_resource.Resource.create.return_value = "resource_obj"
        mock_provider.TracerProvider.return_value = mock_provider

        mock_exporter.OTLPSpanExporter = MagicMock()
        mock_processor.BatchSpanProcessor = MagicMock()

        from agentflow_cli.src.app.core.config.setup_middleware import _setup_otel
        _setup_otel(MagicMock(), settings)

        mock_resource.Resource.create.assert_called_once_with({"service.name": "test-service"})
        mock_provider.TracerProvider.assert_called_once_with(resource="resource_obj")
        mock_exporter.OTLPSpanExporter.assert_called_once_with(endpoint="http://localhost:4317")
        mock_provider.add_span_processor.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)
        mock_instrumentor.FastAPIInstrumentor.instrument_app.assert_called_once()


def test_setup_otel_no_endpoint():
    settings = MagicMock()
    settings.OTEL_ENABLED = True
    settings.OTEL_SERVICE_NAME = "test-service"
    settings.OTEL_EXPORTER_OTLP_ENDPOINT = None

    mock_trace = MagicMock()
    mock_instrumentor = MagicMock()
    mock_resource = MagicMock()
    mock_provider = MagicMock()
    mock_processor = MagicMock()

    modules = {
        "opentelemetry": mock_trace,
        "opentelemetry.trace": mock_trace,
        "opentelemetry.instrumentation.fastapi": mock_instrumentor,
        "opentelemetry.sdk.resources": mock_resource,
        "opentelemetry.sdk.trace": mock_provider,
        "opentelemetry.sdk.trace.export": mock_processor,
    }

    with patch.dict("sys.modules", modules):
        mock_resource.Resource.create.return_value = "resource_obj"
        mock_provider.TracerProvider.return_value = mock_provider
        mock_processor.ConsoleSpanExporter = MagicMock()
        mock_processor.SimpleSpanProcessor = MagicMock()

        from agentflow_cli.src.app.core.config.setup_middleware import _setup_otel
        _setup_otel(MagicMock(), settings)

        mock_processor.ConsoleSpanExporter.assert_called_once()
        mock_processor.SimpleSpanProcessor.assert_called_once()
        mock_provider.add_span_processor.assert_called_once()


def test_setup_otel_grpc_exporter_import_error():
    settings = MagicMock()
    settings.OTEL_ENABLED = True
    settings.OTEL_SERVICE_NAME = "test-service"
    settings.OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"

    mock_trace = MagicMock()
    mock_instrumentor = MagicMock()
    mock_resource = MagicMock()
    mock_provider = MagicMock()
    mock_processor = MagicMock()

    modules = {
        "opentelemetry": mock_trace,
        "opentelemetry.trace": mock_trace,
        "opentelemetry.instrumentation.fastapi": mock_instrumentor,
        "opentelemetry.sdk.resources": mock_resource,
        "opentelemetry.sdk.trace": mock_provider,
        "opentelemetry.sdk.trace.export": mock_processor,
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
    }

    with patch.dict("sys.modules", modules):
        mock_resource.Resource.create.return_value = "resource_obj"
        mock_provider.TracerProvider.return_value = mock_provider

        from agentflow_cli.src.app.core.config.setup_middleware import _setup_otel
        _setup_otel(MagicMock(), settings)
        # Should return gracefully on ImportError of grpc exporter


def test_attach_otel_publisher_import_error():
    with patch.dict("sys.modules", {"agentflow.runtime.publisher.base_publisher": None}):
        from agentflow_cli.src.app.core.config.setup_middleware import _attach_otel_publisher
        container = MagicMock()
        _attach_otel_publisher(container, MagicMock())


def test_attach_otel_publisher_value_error():
    class FakeObservabilityLevel:
        STANDARD = "standard"
        def __init__(self, val):
            raise ValueError("invalid level")

    class FakeOtelPublisher:
        def __init__(self, level):
            self.level = level

    class FakeBasePublisher:
        pass

    modules = {
        "agentflow.runtime.publisher.base_publisher": MagicMock(BasePublisher=FakeBasePublisher),
        "agentflow.runtime.publisher.composite_publisher": MagicMock(),
        "agentflow.runtime.publisher.otel_publisher": MagicMock(
            ObservabilityLevel=FakeObservabilityLevel,
            OtelPublisher=FakeOtelPublisher
        )
    }
    with patch.dict("sys.modules", modules):
        from agentflow_cli.src.app.core.config.setup_middleware import _attach_otel_publisher
        container = MagicMock()
        container.try_get.return_value = None
        settings = MagicMock()
        settings.OTEL_LEVEL = "invalid-level"
        _attach_otel_publisher(container, settings)
        container.bind_instance.assert_called_once()


def test_attach_otel_publisher_no_existing():
    class FakeObservabilityLevel:
        STANDARD = "standard"
        def __init__(self, val):
            self.val = val

    class FakeOtelPublisher:
        def __init__(self, level):
            self.level = level

    class FakeBasePublisher:
        pass

    modules = {
        "agentflow.runtime.publisher.base_publisher": MagicMock(BasePublisher=FakeBasePublisher),
        "agentflow.runtime.publisher.composite_publisher": MagicMock(),
        "agentflow.runtime.publisher.otel_publisher": MagicMock(
            ObservabilityLevel=FakeObservabilityLevel,
            OtelPublisher=FakeOtelPublisher
        )
    }
    with patch.dict("sys.modules", modules):
        from agentflow_cli.src.app.core.config.setup_middleware import _attach_otel_publisher
        container = MagicMock()
        container.try_get.return_value = None
        settings = MagicMock()
        settings.OTEL_LEVEL = "standard"
        _attach_otel_publisher(container, settings)
        container.bind_instance.assert_called_once()


def test_attach_otel_publisher_existing_composite():
    class FakeObservabilityLevel:
        STANDARD = "standard"
        def __init__(self, val):
            self.val = val

    class FakeOtelPublisher:
        def __init__(self, level):
            self.level = level

    class FakeBasePublisher:
        pass

    class FakeCompositePublisher:
        def __init__(self, publishers=None):
            self.publishers = publishers or []
        def add_publisher(self, pub):
            self.publishers.append(pub)

    existing = FakeCompositePublisher()

    modules = {
        "agentflow.runtime.publisher.base_publisher": MagicMock(BasePublisher=FakeBasePublisher),
        "agentflow.runtime.publisher.composite_publisher": MagicMock(CompositePublisher=FakeCompositePublisher),
        "agentflow.runtime.publisher.otel_publisher": MagicMock(
            ObservabilityLevel=FakeObservabilityLevel,
            OtelPublisher=FakeOtelPublisher
        )
    }
    with patch.dict("sys.modules", modules):
        from agentflow_cli.src.app.core.config.setup_middleware import _attach_otel_publisher
        container = MagicMock()
        container.try_get.return_value = existing
        settings = MagicMock()
        settings.OTEL_LEVEL = "standard"

        with patch("agentflow_cli.src.app.core.config.setup_middleware.isinstance", return_value=True):
            _attach_otel_publisher(container, settings)


def test_attach_otel_publisher_existing_single():
    class FakeObservabilityLevel:
        STANDARD = "standard"
        def __init__(self, val):
            self.val = val

    class FakeOtelPublisher:
        def __init__(self, level):
            self.level = level

    class FakeBasePublisher:
        pass

    class FakeCompositePublisher:
        def __init__(self, publishers=None):
            self.publishers = publishers or []

    class SinglePublisher:
        pass

    existing = SinglePublisher()

    modules = {
        "agentflow.runtime.publisher.base_publisher": MagicMock(BasePublisher=FakeBasePublisher),
        "agentflow.runtime.publisher.composite_publisher": MagicMock(CompositePublisher=FakeCompositePublisher),
        "agentflow.runtime.publisher.otel_publisher": MagicMock(
            ObservabilityLevel=FakeObservabilityLevel,
            OtelPublisher=FakeOtelPublisher
        )
    }
    with patch.dict("sys.modules", modules):
        from agentflow_cli.src.app.core.config.setup_middleware import _attach_otel_publisher
        container = MagicMock()
        container.try_get.return_value = existing
        settings = MagicMock()
        settings.OTEL_LEVEL = "standard"

        _attach_otel_publisher(container, settings)
        container.bind_instance.assert_called_once()


class MockSettings:
    OTEL_ENABLED = True
    OTEL_SERVICE_NAME = "test-service"
    OTEL_EXPORTER_OTLP_ENDPOINT = None
    ORIGINS = "http://localhost,http://localhost:3000"
    ALLOWED_HOST = "localhost,127.0.0.1"
    MAX_REQUEST_SIZE = 1024 * 1024
    SECURITY_HEADERS_ENABLED = True
    HSTS_ENABLED = True
    HSTS_MAX_AGE = 31536000
    HSTS_INCLUDE_SUBDOMAINS = True
    HSTS_PRELOAD = True
    FRAME_OPTIONS = "DENY"
    CONTENT_TYPE_OPTIONS = "nosniff"
    XSS_PROTECTION = "1; mode=block"
    REFERRER_POLICY = "no-referrer"
    PERMISSIONS_POLICY = "geolocation=()"
    CSP_POLICY = "default-src 'self'"


def test_setup_middleware_all():
    app = FastAPI()
    settings = MockSettings()

    graph_config = MagicMock()
    rate_limit_config = MagicMock()
    rate_limit_config.backend = "memory"
    rate_limit_config.requests = 100
    rate_limit_config.window = 60
    rate_limit_config.by = "ip"
    rate_limit_config.exclude_paths = None
    rate_limit_config.trusted_proxy_headers = True
    graph_config.rate_limit = rate_limit_config

    container = MagicMock()

    with patch("agentflow_cli.src.app.core.config.setup_middleware.get_settings", return_value=settings), \
         patch("agentflow_cli.src.app.core.config.setup_middleware.init_sentry") as mock_init_sentry, \
         patch("agentflow_cli.src.app.core.config.setup_middleware.build_backend", return_value="mock_backend") as mock_build_backend, \
         patch("agentflow_cli.src.app.core.config.setup_middleware._setup_otel") as mock_setup_otel, \
         patch("agentflow_cli.src.app.core.config.setup_middleware._attach_otel_publisher") as mock_attach:

        setup_middleware(app, graph_config=graph_config, container=container)

        mock_init_sentry.assert_called_once_with(settings)
        mock_build_backend.assert_called_once_with(rate_limit_config, container=container)
        assert app.state.rate_limit_backend == "mock_backend"
        mock_setup_otel.assert_called_once_with(app, settings)
        mock_attach.assert_called_once_with(container, settings)

