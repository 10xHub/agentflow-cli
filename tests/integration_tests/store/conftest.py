"""Shared fixtures for store integration tests."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from agentflow.store import BaseStore, MemorySearchResult, MemoryType
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi


@pytest.fixture
def mock_store():
    """Mock BaseStore for testing."""
    return AsyncMock(spec=BaseStore)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def app(mock_store, mock_auth_user):
    """FastAPI test app with store router."""
    # Import early before binding
    from agentflow_cli.src.app.core.auth.base_auth import BaseAuth

    app = FastAPI()
    setup_middleware(app)

    # Create a fresh container for this test
    container = InjectQ()
    container.bind_instance(BaseStore, mock_store)

    class _NoAuthConfig:
        def auth_config(self):
            return None

    container.bind_instance(GraphConfig, _NoAuthConfig())

    # Create a mock BaseAuth instance
    mock_auth = MagicMock(spec=BaseAuth)
    mock_auth.authenticate.return_value = mock_auth_user
    container.bind_instance(BaseAuth, mock_auth)

    # Setup FastAPI with the container
    setup_fastapi(container, app)

    # Mock authentication to provide a user
    with patch(
        "agentflow_cli.src.app.core.auth.auth_backend.verify_current_user",
        return_value=mock_auth_user,
    ):
        from agentflow_cli.src.app.routers.store.router import router as store_router

        app.include_router(store_router)

        # Debug: Check OpenAPI
        openapi = app.openapi()
        if "/v1/store/memories" in openapi.get("paths", {}):
            endpoint = openapi["paths"]["/v1/store/memories"]["post"]
            print(f"DEBUG: /v1/store/memories parameters: {endpoint.get('parameters', [])}")

        yield app


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return TestClient(app)


@pytest.fixture
def unauth_app(mock_store):
    """FastAPI test app without auth patch, but with DI patched and safe defaults.

    This allows testing endpoints without authentication while avoiding
    serialization issues from AsyncMock default returns.
    """
    # Import early before binding
    from agentflow_cli.src.app.core.auth.base_auth import BaseAuth

    app = FastAPI()
    setup_middleware(app)

    # Provide safe default return values to avoid pydantic/serialization issues
    mock_store.astore.return_value = str(uuid4())
    mock_store.asearch.return_value = []
    mock_store.aget.return_value = None
    mock_store.aget_all.return_value = []
    mock_store.aupdate.return_value = {"updated": True}
    mock_store.adelete.return_value = {"deleted": True}
    mock_store.aforget_memory.return_value = {"count": 0}

    # Setup InjectQ container and bind BaseStore to mocked store
    container = InjectQ()
    container.bind_instance(BaseStore, mock_store)

    class _NoAuthConfig:
        def auth_config(self):
            return None

    container.bind_instance(GraphConfig, _NoAuthConfig())

    # Create a mock BaseAuth instance
    mock_auth = MagicMock(spec=BaseAuth)
    mock_auth.authenticate.return_value = {}
    container.bind_instance(BaseAuth, mock_auth)

    setup_fastapi(container, app)

    # Patch auth to no-op so BaseAuth DI is not required in unauthenticated tests
    with patch(
        "agentflow_cli.src.app.core.auth.auth_backend.verify_current_user",
        return_value={},
    ):
        from agentflow_cli.src.app.routers.store.router import router as store_router

        app.include_router(store_router)
        yield app


@pytest.fixture
def unauth_client(unauth_app):
    """Test client without auth override for authentication behavior tests."""
    return TestClient(unauth_app)


@pytest.fixture
def auth_headers():
    """Authentication headers."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_memory_id():
    """Sample memory ID."""
    return str(uuid4())


@pytest.fixture
def sample_memory_result(sample_memory_id):
    """Sample MemorySearchResult."""
    return MemorySearchResult(
        id=sample_memory_id,
        content="This is a test memory",
        memory_type=MemoryType.EPISODIC,
        metadata={"key": "value"},
        score=0.95,
    )


@pytest.fixture
def sample_memory_results(sample_memory_id):
    """Sample list of MemorySearchResult."""
    return [
        MemorySearchResult(
            id=sample_memory_id,
            content="First memory",
            memory_type=MemoryType.EPISODIC,
            metadata={"index": 1},
            score=0.95,
        ),
        MemorySearchResult(
            id=str(uuid4()),
            content="Second memory",
            memory_type=MemoryType.SEMANTIC,
            metadata={"index": 2},
            score=0.85,
        ),
    ]
