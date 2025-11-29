from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.routers.setup_router import init_routes


HTTP_NOT_FOUND = 404
HTTP_OK = 200


def test_init_routes_includes_ping_only():
    app = FastAPI()
    setup_middleware(app)
    init_routes(app)
    client = TestClient(app)

    r = client.get("/ping")
    assert r.status_code == HTTP_OK
    assert r.json()["data"] == "pong"

    # Graph and checkpointer routers are present but actual endpoints may be complex.
    # Just verify that non-existent path returns 404 to execute include_router lines.
    r2 = client.get("/non-existent")
    assert r2.status_code == HTTP_NOT_FOUND
