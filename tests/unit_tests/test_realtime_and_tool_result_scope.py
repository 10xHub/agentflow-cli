"""Clients may not reach tools the server did not offer them (M1).

- A tool result is accepted only as the answer to a remote tool call that is waiting for one.
- A realtime init frame may not widen the agent's tool tags, or pick an unlisted model.
"""

# ruff: noqa: S101

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from agentflow.core.graph import ToolNode
from agentflow.core.state import AgentState, Message
from agentflow.core.state.message_block import TextBlock, ToolResultBlock

from agentflow_cli.src.app.core.config.graph_config import WebSocketConfig
from agentflow_cli.src.app.routers.graph.services.graph_service import GraphService


def _assistant_call(call_id: str, name: str) -> Message:
    return Message(
        role="assistant",
        content=[TextBlock(text="")],
        tools_calls=[{"id": call_id, "type": "function", "function": {"name": name}}],
    )


def _result(call_id: str) -> Message:
    return Message(role="tool", content=[ToolResultBlock(call_id=call_id, output="ok")])


def _service(context=None, websocket=None, live_tags=None) -> GraphService:
    tool_node = ToolNode([])
    tool_node.set_remote_tool([{"type": "function", "function": {"name": "get_location"}}])
    nodes = {"tools": SimpleNamespace(func=tool_node)}

    graph = MagicMock()
    graph._state_graph = SimpleNamespace(nodes=nodes)
    live = SimpleNamespace(
        func=SimpleNamespace(realtime_config=SimpleNamespace(tools_tags=live_tags))
    )
    graph._find_live_nodes = lambda: [("live", live)]

    service = GraphService.__new__(GraphService)
    service._graph = graph
    service.checkpointer = MagicMock()
    state = AgentState(context=context) if context is not None else None
    service.checkpointer.aget_state = AsyncMock(return_value=state)
    service.config = SimpleNamespace(websocket=websocket or WebSocketConfig(max_connections=None))
    return service


CONFIG = {"thread_id": "t1", "user": {"user_id": "alice"}}


# ---------------------------------------------------------------------------
# tool results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_for_a_pending_remote_call_is_accepted():
    service = _service([_assistant_call("c1", "get_location")])
    await service._check_tool_results([_result("c1")], CONFIG)


@pytest.mark.asyncio
async def test_messages_without_tool_results_skip_the_lookup():
    service = _service()
    await service._check_tool_results([Message.text_message("hi")], CONFIG)
    service.checkpointer.aget_state.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("context", "call_id"),
    [
        (None, "c1"),  # new thread: nothing was requested
        ([_assistant_call("c1", "get_location")], "c2"),  # never requested
        ([_assistant_call("c1", "get_location"), _result("c1")], "c1"),  # already answered
        ([_assistant_call("c1", "delete_user")], "c1"),  # a server tool, not a remote one
    ],
)
async def test_unrequested_results_are_rejected(context, call_id):
    service = _service(context)
    with pytest.raises(ValueError, match="waiting for a result"):
        await service._check_tool_results([_result(call_id)], CONFIG)


@pytest.mark.asyncio
async def test_a_call_cannot_be_answered_twice_in_one_request():
    service = _service([_assistant_call("c1", "get_location")])
    with pytest.raises(ValueError, match="only once"):
        await service._check_tool_results([_result("c1"), _result("c1")], CONFIG)


# ---------------------------------------------------------------------------
# realtime init frame
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(["weather", "admin"], ["weather"]), (["admin"], None), ([], None), ("weather", ["weather"])],
)
def test_tools_tags_can_only_narrow(requested, expected):
    service = _service(live_tags=["weather", "math"])
    result = service._restrict_realtime_overrides({"tools_tags": requested})
    assert result.get("tools_tags") == expected


def test_tools_tags_narrow_an_unfiltered_agent():
    service = _service(live_tags=None)
    assert service._restrict_realtime_overrides({"tools_tags": ["weather"]}) == {
        "tools_tags": ["weather"]
    }


def test_unlisted_model_is_ignored():
    service = _service()
    assert service._restrict_realtime_overrides({"model": "pricey", "voice": "Puck"}) == {
        "voice": "Puck"
    }


def test_listed_model_is_honoured():
    ws = WebSocketConfig.from_dict({"realtime_models": ["gemini-live-b"]})
    service = _service(websocket=ws)
    assert service._restrict_realtime_overrides({"model": "gemini-live-b"}) == {
        "model": "gemini-live-b"
    }


def test_realtime_models_must_be_strings():
    with pytest.raises(ValueError, match="realtime_models"):
        WebSocketConfig.from_dict({"realtime_models": "gemini"})


# ---------------------------------------------------------------------------
# L11: realtime errors do not echo internal exception text in production
# ---------------------------------------------------------------------------


def test_realtime_error_text_is_generic_in_production(monkeypatch):
    import importlib

    router = importlib.import_module("agentflow_cli.src.app.routers.graph.router")
    error = ValueError("connect to postgres://admin:hunter2@10.0.0.5 failed")

    monkeypatch.setattr(
        "agentflow_cli.src.app.core.config.settings.get_settings",
        lambda: SimpleNamespace(MODE="production"),
    )
    assert "hunter2" not in router._client_error(error)

    monkeypatch.setattr(
        "agentflow_cli.src.app.core.config.settings.get_settings",
        lambda: SimpleNamespace(MODE="development"),
    )
    assert router._client_error(error) == str(error)
