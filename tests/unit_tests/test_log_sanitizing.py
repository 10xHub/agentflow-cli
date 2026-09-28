"""Logs must not carry tokens or raw request bodies (M7)."""

# ruff: noqa: S101

import io
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from agentflow_cli.src.app.core.config import setup_logs
from agentflow_cli.src.app.core.exceptions.handle_errors import init_errors_handler
from agentflow_cli.src.app.core.utils.log_sanitizer import SanitizingFormatter, redact_text


JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhbGljZSJ9.c2lnbmF0dXJlLXZhbHVl"


def test_tokens_inside_a_message_are_redacted():
    text = redact_text(f"auth header was Bearer {JWT} and raw {JWT}")
    assert JWT not in text
    assert "Bearer ***REDACTED***" in text


def test_formatter_redacts_f_string_messages():
    formatter = SanitizingFormatter(logging.Formatter("%(message)s"))
    record = logging.LogRecord("x", logging.INFO, __file__, 1, f"token {JWT}", None, None)
    assert JWT not in formatter.format(record)


def test_app_loggers_go_through_the_sanitizing_handler():
    setup_logs.init_logger(logging.INFO)
    setup_logs.init_logger(logging.INFO)  # idempotent: one handler, not two
    for name in ("agentflow-cli", "agentflow_api", "agentflow_cli"):
        logger = logging.getLogger(name)
        sanitizing = [h for h in logger.handlers if isinstance(h.formatter, SanitizingFormatter)]
        assert len(sanitizing) == 1
        assert logger.propagate is False


class _Body(BaseModel):
    items: list[int]


@pytest.fixture
def captured():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("agentflow-cli")
    logger.addHandler(handler)
    yield stream
    logger.removeHandler(handler)


def test_validation_errors_do_not_log_the_body(captured):
    app = FastAPI()
    init_errors_handler(app)

    @app.middleware("http")
    async def _request_id(request, call_next):
        request.state.request_id = "r1"
        request.state.timestamp = "t"
        return await call_next(request)

    @app.post("/x")
    async def _x(body: _Body):
        return {}

    response = TestClient(app).post("/x", json={"items": ["secret-value-123"]})
    assert response.status_code == 422
    logged = captured.getvalue()
    assert "body.items.0" in logged
    assert "secret-value-123" not in logged
