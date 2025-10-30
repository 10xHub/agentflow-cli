from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.routers.ping.router import router as ping_router


HTTP_OK = 200


def test_ping_route_success():
    app = FastAPI()
    setup_middleware(app)
    app.include_router(ping_router)
    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == HTTP_OK
    assert r.json()["data"] == "pong"
