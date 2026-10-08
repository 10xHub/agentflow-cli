"""Unit tests for request size limit middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from tenxgraph_api.src.app.core.middleware.request_limits import RequestSizeLimitMiddleware


@pytest.fixture
def app_with_limit():
    """Create a FastAPI app with request size limit middleware."""
    app = FastAPI()

    # Add middleware with 1KB limit for testing
    app.add_middleware(RequestSizeLimitMiddleware, max_size=1024)

    @app.post("/test")
    async def test_endpoint(data: dict):
        return {"status": "ok", "data": data}

    return app


def test_request_under_limit(app_with_limit):
    """Test that requests under the size limit are allowed."""
    client = TestClient(app_with_limit)

    # Small payload (under 1KB)
    small_data = {"message": "Hello, World!"}
    response = client.post("/test", json=small_data)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_over_limit(app_with_limit):
    """Test that requests over the size limit are rejected."""
    client = TestClient(app_with_limit)

    # Large payload (over 1KB)
    large_data = {"message": "x" * 2000}
    response = client.post("/test", json=large_data)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
    assert "request_id" in response.json()["metadata"]


def test_request_without_content_length(app_with_limit):
    """Test that requests without content-length header are allowed."""
    client = TestClient(app_with_limit)

    # TestClient automatically adds content-length, but if it's missing
    # the middleware should allow the request through
    response = client.post("/test", json={"message": "test"})

    # Should succeed since small payload
    assert response.status_code == 200


def test_middleware_with_default_limit():
    """Test middleware with default 10MB limit."""
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware)  # Default 10MB

    @app.post("/test")
    async def test_endpoint(data: dict):
        return {"status": "ok"}

    client = TestClient(app)
    response = client.post("/test", json={"message": "test"})

    assert response.status_code == 200


def test_error_response_format(app_with_limit):
    """Test that error response has correct format."""
    client = TestClient(app_with_limit)

    large_data = {"message": "x" * 2000}
    response = client.post("/test", json=large_data)

    assert response.status_code == 413

    json_response = response.json()
    assert "error" in json_response
    assert "metadata" in json_response

    error = json_response["error"]
    assert error["code"] == "REQUEST_TOO_LARGE"
    assert "max_size_bytes" in error
    assert "max_size_mb" in error
    assert error["max_size_bytes"] == 1024
    assert error["max_size_mb"] == 1024 / (1024 * 1024)


# ---------------------------------------------------------------------------
# Bodies without Content-Length (chunked) must be limited as they stream in.
# ---------------------------------------------------------------------------


def _chunks(total: int, size: int = 256):
    sent = 0
    while sent < total:
        piece = min(size, total - sent)
        sent += piece
        yield b" " * piece


@pytest.fixture
def guarded_app():
    """1 KB limit, with an auth-like dependency that records whether it ran."""
    from fastapi import Depends, File, UploadFile

    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_size=1024)
    calls: list[str] = []

    def auth():
        calls.append("auth")

    @app.post("/json")
    async def json_endpoint(data: dict, _=Depends(auth)):
        return {"ok": True}

    @app.post("/upload")
    async def upload_endpoint(file: UploadFile = File(...), _=Depends(auth)):
        return {"ok": True}

    return app, calls


def test_chunked_body_over_limit_is_rejected_before_the_route(guarded_app):
    app, calls = guarded_app
    body = b'{"message": "' + b"x" * 5000 + b'"}'

    def gen():
        yield from (body[i : i + 256] for i in range(0, len(body), 256))

    response = TestClient(app).post(
        "/json", content=gen(), headers={"content-type": "application/json"}
    )

    assert response.status_code == 413
    assert calls == []  # the body was cut off before any dependency ran


def test_chunked_body_under_limit_is_allowed(guarded_app):
    app, calls = guarded_app
    body = b'{"message": "hi"}'
    response = TestClient(app).post(
        "/json", content=iter([body]), headers={"content-type": "application/json"}
    )
    assert response.status_code == 200
    assert calls == ["auth"]


def test_chunked_multipart_upload_over_limit_is_rejected(guarded_app):
    app, calls = guarded_app
    boundary = "b0undary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.bin"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def gen():
        yield head
        yield from _chunks(50_000)
        yield tail

    response = TestClient(app).post(
        "/upload",
        content=gen(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 413
    assert calls == []


def test_invalid_content_length_is_a_client_error(app_with_limit):
    response = TestClient(app_with_limit).post(
        "/test", content=b"{}", headers={"content-length": "abc"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# L7: the upload route has room for MEDIA_MAX_SIZE_MB
# ---------------------------------------------------------------------------


def _path_limited_app() -> TestClient:
    app = FastAPI()
    app.add_middleware(
        RequestSizeLimitMiddleware, max_size=1024, path_limits={"/v1/files/upload": 4096}
    )

    @app.post("/v1/files/upload")
    async def upload(request: Request):
        return {"size": len(await request.body())}

    @app.post("/other")
    async def other(request: Request):
        return {"size": len(await request.body())}

    return TestClient(app)


def test_upload_route_uses_its_own_limit():
    client = _path_limited_app()
    assert client.post("/v1/files/upload", content=b"x" * 3000).status_code == 200
    assert client.post("/v1/files/upload", content=b"x" * 5000).status_code == 413
    assert client.post("/other", content=b"x" * 3000).status_code == 413


def test_upload_limit_follows_the_media_setting(monkeypatch):
    from tenxgraph_api.src.app.core.config import setup_middleware

    monkeypatch.setattr(
        "tenxgraph_api.src.app.core.config.media_settings.get_media_settings",
        lambda: type("S", (), {"MEDIA_MAX_SIZE_MB": 25.0})(),
    )
    limits = setup_middleware._upload_path_limits(10 * 1024 * 1024)
    assert limits["/v1/files/upload"] > 25 * 1024 * 1024
    assert setup_middleware._upload_path_limits(100 * 1024 * 1024) == {}
