from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.core.exceptions.handle_errors import init_errors_handler


HTTP_NOT_FOUND = 404


def test_http_exception_handler_returns_error_payload():
    import os

    # Ensure development mode for this test
    os.environ["MODE"] = "development"

    from agentflow_cli.src.app.core.config.settings import get_settings

    get_settings.cache_clear()

    app = FastAPI()
    setup_middleware(app)
    init_errors_handler(app)

    @app.get("/boom")
    def boom():
        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app)
    r = client.get("/boom")
    assert r.status_code == HTTP_NOT_FOUND
    body = r.json()
    assert body["error"]["code"] == "HTTPException"
    assert body["error"]["message"] == "nope"

    # Cleanup
    if "MODE" in os.environ:
        del os.environ["MODE"]
