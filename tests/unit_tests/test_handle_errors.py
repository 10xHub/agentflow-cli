from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from pyagenity_api.src.app.core.config.setup_middleware import setup_middleware
from pyagenity_api.src.app.core.exceptions.handle_errors import init_errors_handler


HTTP_NOT_FOUND = 404


def test_http_exception_handler_returns_error_payload():
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
