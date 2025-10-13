import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from agentflow_cli.src.app.core.config.settings import Settings
from agentflow_cli.src.app.utils.callable_helper import call_sync_or_async
from agentflow_cli.src.app.utils.parse_output import (
    parse_message_output,
    parse_state_output,
)


class _StateModel(BaseModel):
    a: int
    b: str
    execution_meta: dict[str, Any] | None = None


class _MessageModel(BaseModel):
    content: str
    raw: dict[str, Any] | None = None


@pytest.mark.parametrize("is_debug", [True, False])
def test_parse_state_output(is_debug: bool):
    settings = Settings(IS_DEBUG=is_debug)
    model = _StateModel(a=1, b="x", execution_meta={"duration": 123})
    out = parse_state_output(settings, model)
    # execution_meta excluded only in debug mode per implementation
    if is_debug:
        assert "execution_meta" not in out
    else:
        assert out["execution_meta"] == {"duration": 123}
    assert out["a"] == 1 and out["b"] == "x"


@pytest.mark.parametrize("is_debug", [True, False])
def test_parse_message_output(is_debug: bool):
    settings = Settings(IS_DEBUG=is_debug)
    model = _MessageModel(content="hello", raw={"tokens": 5})
    out = parse_message_output(settings, model)
    if is_debug:
        assert "raw" not in out
    else:
        assert out["raw"] == {"tokens": 5}
    assert out["content"] == "hello"


def test_call_sync_or_async_sync_function():
    def sync_fn(x: int, y: int) -> int:
        return x + y

    result = asyncio.run(call_sync_or_async(sync_fn, 2, 3))
    assert result == 5


def test_call_sync_or_async_async_function():
    async def async_fn(x: int) -> int:
        await asyncio.sleep(0)  # yield control
        return x * 2

    result = asyncio.run(call_sync_or_async(async_fn, 4))
    assert result == 8


def test_call_sync_or_async_sync_returns_awaitable():
    # Edge case: sync function returns coroutine (rare but allowed in implementation)
    async def inner() -> str:
        return "done"

    def sync_returns_coroutine():
        return inner()

    result = asyncio.run(call_sync_or_async(sync_returns_coroutine))
    assert result == "done"
