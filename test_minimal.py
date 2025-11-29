"""Minimal test to isolate the issue."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from agentflow.store import BaseStore
from agentflow_cli.src.app.core.auth.base_auth import BaseAuth
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi


def test_minimal():
    """Minimal test to check if the setup works."""
    # Create mock store
    mock_store = AsyncMock(spec=BaseStore)
    mock_store.aforget_memory.return_value = {"count": 2}

    # Create mock user
    mock_auth_user = {"user_id": "test-123"}

    # Create app
    app = FastAPI()
    setup_middleware(app)

    # Create container
    container = InjectQ()
    container.bind_instance(BaseStore, mock_store)

    class _NoAuthConfig:
        def auth_config(self):
            return None

    container.bind_instance(GraphConfig, _NoAuthConfig())

    # Create mock auth
    mock_auth = MagicMock(spec=BaseAuth)
    mock_auth.authenticate.return_value = mock_auth_user
    container.bind_instance(BaseAuth, mock_auth)

    # Setup FastAPI
    setup_fastapi(container, app)

    # Patch auth BEFORE importing router
    with patch(
        "agentflow_cli.src.app.core.auth.auth_backend.verify_current_user",
        return_value=mock_auth_user,
    ):
        from agentflow_cli.src.app.routers.store.router import router as store_router

        app.include_router(store_router)

        # Create client INSIDE the patch context
        client = TestClient(app)

        # Check OpenAPI schema
        openapi_schema = app.openapi()
        forget_endpoint = openapi_schema["paths"]["/v1/store/memories/forget"]["post"]
        print(f"Forget endpoint parameters: {forget_endpoint.get('parameters', [])}")
        print(f"Forget endpoint requestBody: {forget_endpoint.get('requestBody', {})}")

        # Test request
        payload = {"memory_type": "semantic"}
        response = client.post("/v1/store/memories/forget", json=payload)

        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

        assert response.status_code == 200


if __name__ == "__main__":
    test_minimal()
