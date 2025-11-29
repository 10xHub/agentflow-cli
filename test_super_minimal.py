"""Super minimal test."""

from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from injectq import InjectQ
from injectq.integrations.fastapi import setup_fastapi
from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow.store import BaseStore
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.auth.base_auth import BaseAuth

app = FastAPI()
setup_middleware(app)

# Create mock store
mock_store = AsyncMock(spec=BaseStore)

# Create container
container = InjectQ()
container.bind_instance(BaseStore, mock_store)


class _NoAuthConfig:
    def auth_config(self):
        return None


container.bind_instance(GraphConfig, _NoAuthConfig())

# Create mock auth
mock_auth = MagicMock(spec=BaseAuth)
mock_auth.authenticate.return_value = {"user_id": "test"}
container.bind_instance(BaseAuth, mock_auth)

# Setup FastAPI
setup_fastapi(container, app)

# Import the router directly
from agentflow_cli.src.app.routers.store.router import router as store_router

app.include_router(store_router)

client = TestClient(app)

# Check OpenAPI
openapi = app.openapi()
forget_endpoint = openapi["paths"]["/v1/store/memories/forget"]["post"]
print(f"Parameters: {forget_endpoint.get('parameters', [])}")
