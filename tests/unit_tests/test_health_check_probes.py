"""The /ping health check works behind ALLOWED_HOST and rate limiting (M9)."""

# ruff: noqa: S101, PLR2004

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tenxgraph_api.src.app.core.config.graph_config import RateLimitConfig
from tenxgraph_api.src.app.core.config.setup_middleware import (
    HealthCheckAwareTrustedHostMiddleware,
)
from tenxgraph_api.src.app.core.middleware.rate_limit import (
    RateLimitDecision,
    RateLimitMiddleware,
)


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"data": "pong"}

    @app.get("/v1/data")
    def data():
        return {"ok": True}

    return app


def test_probe_passes_the_host_check_from_any_host():
    app = _app()
    app.add_middleware(HealthCheckAwareTrustedHostMiddleware, allowed_hosts=["api.example.com"])
    client = TestClient(app, base_url="http://10.0.0.7:8000")

    assert client.get("/ping").status_code == 200
    assert client.get("/v1/data").status_code == 400  # other paths are still host-checked


def test_allowed_host_still_reaches_every_path():
    app = _app()
    app.add_middleware(HealthCheckAwareTrustedHostMiddleware, allowed_hosts=["api.example.com"])
    client = TestClient(app, base_url="http://api.example.com")
    assert client.get("/v1/data").status_code == 200


class _DenyAll:
    """A backend that is down with fail_open=false, or simply exhausted."""

    async def check(self, key, *, limit, window):
        return RateLimitDecision(allowed=False, remaining=0, reset_after=30)

    async def close(self):
        pass


def test_probe_is_never_rate_limited():
    app = _app()
    config = RateLimitConfig.from_dict({"enabled": True, "backend": "memory", "requests": 1})
    app.add_middleware(RateLimitMiddleware, config=config, backend=_DenyAll())
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/v1/data").status_code == 429
