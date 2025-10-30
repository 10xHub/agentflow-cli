from fastapi.testclient import TestClient

from agentflow_cli.src.app.main import app

HTTP_OK = 200


def test_ping_endpoint_returns_pong():
    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == HTTP_OK
    data = resp.json()
    assert data["data"] == "pong"
    assert "metadata" in data and isinstance(data["metadata"], dict)
    # metadata should contain message and timestamp
    meta = data["metadata"]
    assert meta.get("message") == "OK"
    assert "request_id" in meta and isinstance(meta["request_id"], str)
    assert "timestamp" in meta
