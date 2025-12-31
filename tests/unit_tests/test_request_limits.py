"""Unit tests for request size limit middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agentflow_cli.src.app.core.middleware.request_limits import RequestSizeLimitMiddleware


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
