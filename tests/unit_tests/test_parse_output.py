import os

from pydantic import BaseModel

from agentflow_cli.src.app.core.config.settings import Settings
from agentflow_cli.src.app.utils.parse_output import parse_message_output, parse_state_output


class StateModel(BaseModel):
    a: int
    b: int
    execution_meta: str | None = None


class MessageModel(BaseModel):
    text: str
    raw: dict | None = None


def test_parse_state_output_debug_true(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    settings = Settings(
        IS_DEBUG=True,
    )
    model = StateModel(a=1, b=2, execution_meta="meta")
    out = parse_state_output(settings, model)
    # Since parse_state_output doesn't filter execution_meta (commented out),
    # it should always be present regardless of debug mode
    assert out == {"a": 1, "b": 2, "execution_meta": "meta"}


def test_parse_state_output_debug_false(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    settings = Settings(
        IS_DEBUG=False,
    )
    model = StateModel(a=1, b=2, execution_meta="meta")
    out = parse_state_output(settings, model)
    assert out == {"a": 1, "b": 2, "execution_meta": "meta"}


def test_parse_message_output_debug_true(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    settings = Settings(
        IS_DEBUG=True,
    )
    model = MessageModel(text="hello", raw={"tokens": 3})
    out = parse_message_output(settings, model)
    # Since parse_message_output doesn't filter raw (commented out),
    # it should always be present regardless of debug mode
    assert out == {"text": "hello", "raw": {"tokens": 3}}


def test_parse_message_output_debug_false(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    settings = Settings(
        IS_DEBUG=False,
    )
    model = MessageModel(text="hello", raw={"tokens": 3})
    out = parse_message_output(settings, model)
    assert out == {"text": "hello", "raw": {"tokens": 3}}
