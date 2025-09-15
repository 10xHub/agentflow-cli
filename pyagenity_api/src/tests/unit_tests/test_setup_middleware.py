from fastapi import FastAPI
from fastapi.testclient import TestClient

from pyagenity_api.src.app.core.config.setup_middleware import setup_middleware


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
