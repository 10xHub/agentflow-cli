"""Shared fixtures for store integration tests."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from agentflow.store import BaseStore, MemorySearchResult, MemoryType
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.routers.store.router import router as store_router


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
    app = FastAPI()
    setup_middleware(app)
    app.include_router(store_router)

    # Mock the dependency injection for StoreService
    with patch("agentflow_cli.src.app.routers.store.router.InjectAPI") as mock_inject:
        from agentflow_cli.src.app.routers.store.services.store_service import (
            StoreService,
        )

        # Create a StoreService with the mocked store
        mock_service = StoreService(store=mock_store)
        mock_inject.return_value = mock_service

        # Mock authentication
        with patch(
            "agentflow_cli.src.app.routers.store.router.verify_current_user",
            return_value=mock_auth_user,
        ):
            yield app


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return TestClient(app)


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
