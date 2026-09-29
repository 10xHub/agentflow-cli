"""AG-UI endpoint end to end: real app wiring, real graph, real checkpointer.

The graph is deterministic (no LLM). It answers a weather question through a server tool and
a color request through a client-side (remote) tool, so both tool paths and the multi-turn
thread handling run for real.
"""

# ruff: noqa: S101

from __future__ import annotations

import json
from typing import Any

import pytest


pytest.importorskip("ag_ui")

from ag_ui.core import EventType
from ag_ui.core.events import Event
from agentflow.core.graph import CompiledGraph, StateGraph, ToolNode
from agentflow.core.state import AgentState, Message, TextBlock, ToolCallBlock
from agentflow.storage.checkpointer import BaseCheckpointer, InMemoryCheckpointer
from agentflow.utils.constants import END
from injectq import InjectQ
from pydantic import TypeAdapter

from agentflow_cli.src.app.routers.ag_ui import router as ag_ui_router

from .conftest import OwnershipAuthz, build_app, make_client, user_headers


_EVENT = TypeAdapter(Event)


class ColorState(AgentState):
    city: str = ""


async def get_weather(city: str) -> dict:
    """Canned weather report."""
    return {"city": city, "temp_c": 31}


def _call(call_id: str, name: str, args: dict) -> Message:
    return Message(
        role="assistant",
        content=[ToolCallBlock(id=call_id, name=name, args=args)],
        tools_calls=[
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ],
    )


async def main_node(state: ColorState):
    last = state.context[-1]
    if last.role == "tool":
        return Message(role="assistant", content=[TextBlock(text=f"Result: {last.text()}")])
    if "color" in last.text().lower():
        return _call("call-color", "pick_color", {"hint": "calm"})
    state.city = "Dhaka"
    return _call("call-weather", "get_weather", {"city": "Dhaka"})


def _route(state: AgentState) -> str:
    last = state.context[-1]
    if last.role == "assistant" and last.tools_calls:
        return "TOOL"
    if last.role == "tool" and not last.metadata.get("is_remote"):
        return "MAIN"
    return END


def _graph(checkpointer: BaseCheckpointer) -> CompiledGraph:
    graph = StateGraph(ColorState())
    graph.add_node("MAIN", main_node)
    graph.add_node("TOOL", ToolNode([get_weather]))
    graph.add_conditional_edges("MAIN", _route, {"TOOL": "TOOL", END: END})
    graph.add_conditional_edges("TOOL", _route, {"MAIN": "MAIN", END: END})
    graph.set_entry_point("MAIN")
    compiled = graph.compile(checkpointer=checkpointer)
    compiled.attach_remote_tools(
        [
            {
                "type": "function",
                "function": {
                    "name": "pick_color",
                    "description": "Ask the user to pick a color.",
                    "parameters": {"type": "object", "properties": {"hint": {"type": "string"}}},
                },
            }
        ],
        "TOOL",
    )
    return compiled


class _Config:
    """GraphConfig stand-in: auth on, no thread name generator."""

    thread_name_generator_path = None

    def auth_config(self) -> str:
        return "custom"


@pytest.fixture(scope="module")
def graph_and_checkpointer():
    """One graph and checkpointer for the module; each test uses its own thread.

    The core resolves the checkpointer it persists through from the global container once per
    process (``sync_data`` takes it as an ``Inject[...]`` default), so every run in this module
    has to share one instance. ``test_mode`` keeps the bindings out of the shared global
    container other tests rely on.
    """
    with InjectQ.test_mode():
        checkpointer = InMemoryCheckpointer()
        yield _graph(checkpointer), checkpointer


@pytest.fixture
def setup(graph_and_checkpointer):
    from agentflow_cli.src.app.core.config.graph_config import GraphConfig

    graph, checkpointer = graph_and_checkpointer
    authz = OwnershipAuthz()
    app = build_app(
        routers=[ag_ui_router],
        authz=authz,
        checkpointer=checkpointer,
        extra_bindings={CompiledGraph: graph, GraphConfig: _Config()},
    )
    return make_client(app), checkpointer, authz


def _events(response) -> list[Any]:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for frame in response.text.split("\n\n"):
        if frame.startswith("data: "):
            events.append(_EVENT.validate_python(json.loads(frame[len("data: ") :])))
    return events


def _types(events) -> list[str]:
    return [e.type for e in events]


def _body(thread_id: str, messages: list[dict], **extra) -> dict:
    return {"threadId": thread_id, "runId": f"run-{len(messages)}", "messages": messages, **extra}


def test_weather_run_streams_tool_call_result_text_and_state(setup):
    client, checkpointer, _ = setup
    response = client.post(
        "/v1/ag-ui",
        json=_body("t1", [{"id": "u1", "role": "user", "content": "weather?"}]),
        headers=user_headers("alice"),
    )
    events = _events(response)
    types = _types(events)
    assert types[0] == EventType.RUN_STARTED
    assert types[-1] == EventType.RUN_FINISHED
    start = next(e for e in events if e.type == EventType.TOOL_CALL_START)
    assert start.tool_call_name == "get_weather"
    result = next(e for e in events if e.type == EventType.TOOL_CALL_RESULT)
    assert result.tool_call_id == start.tool_call_id
    assert '"temp_c": 31' in result.content
    text = "".join(e.delta for e in events if e.type == EventType.TEXT_MESSAGE_CONTENT)
    assert "temp_c" in text
    assert {"city": "Dhaka"} in [e.snapshot for e in events if e.type == EventType.STATE_SNAPSHOT]
    assert {"STEP_STARTED", "STEP_FINISHED"} <= {str(t.value) for t in types}


def test_frontend_tool_round_trip(setup):
    client, checkpointer, _ = setup
    history = [{"id": "u1", "role": "user", "content": "pick a color"}]
    first = _events(
        client.post("/v1/ag-ui", json=_body("t2", history), headers=user_headers("alice"))
    )
    call = next(e for e in first if e.type == EventType.TOOL_CALL_START)
    assert call.tool_call_name == "pick_color"
    # The client runs it: the server must not answer, and the run ends normally.
    assert EventType.TOOL_CALL_RESULT not in _types(first)
    assert _types(first)[-1] == EventType.RUN_FINISHED

    # The client resends the whole conversation plus its tool result (with a fresh id).
    history += [
        {
            "id": call.parent_message_id,
            "role": "assistant",
            "toolCalls": [
                {
                    "id": call.tool_call_id,
                    "type": "function",
                    "function": {"name": "pick_color", "arguments": '{"hint": "calm"}'},
                }
            ],
        },
        {"id": "client-minted", "role": "tool", "toolCallId": call.tool_call_id, "content": "teal"},
    ]
    second = _events(
        client.post("/v1/ag-ui", json=_body("t2", history), headers=user_headers("alice"))
    )
    text = "".join(e.delta for e in second if e.type == EventType.TEXT_MESSAGE_CONTENT)
    assert text == "Result: teal"
    assert _types(second)[-1] == EventType.RUN_FINISHED


def test_second_turn_sends_only_the_new_message(setup):
    client, checkpointer, _ = setup
    first = [{"id": "u1", "role": "user", "content": "weather?"}]
    _events(client.post("/v1/ag-ui", json=_body("t3", first), headers=user_headers("alice")))

    history = [
        *first,
        {"id": "a-any", "role": "assistant", "content": "Result: ..."},
        {"id": "u2", "role": "user", "content": "and again?"},
    ]
    _events(client.post("/v1/ag-ui", json=_body("t3", history), headers=user_headers("alice")))

    import anyio

    state = anyio.run(checkpointer.aget_state, {"thread_id": "t3", "user_id": "alice"})
    user_ids = [m.message_id for m in state.context if m.role == "user"]
    assert user_ids == ["u1", "u2"]


def test_resending_a_known_message_does_not_rerun_the_graph(setup):
    client, _, _ = setup
    body = _body("t4", [{"id": "u1", "role": "user", "content": "weather?"}])
    _events(client.post("/v1/ag-ui", json=body, headers=user_headers("alice")))
    again = _events(client.post("/v1/ag-ui", json=body, headers=user_headers("alice")))
    assert EventType.TOOL_CALL_START not in _types(again)
    assert _types(again)[0] == EventType.RUN_STARTED
    assert _types(again)[-1] == EventType.RUN_FINISHED


def test_other_users_thread_is_forbidden(setup):
    client, _, authz = setup
    authz.own("thread-A", "alice")
    response = client.post(
        "/v1/ag-ui",
        json=_body("thread-A", [{"id": "u1", "role": "user", "content": "hi"}]),
        headers=user_headers("mallory"),
    )
    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(setup):
    client, _, _ = setup
    response = client.post(
        "/v1/ag-ui", json=_body("t5", [{"id": "u1", "role": "user", "content": "hi"}])
    )
    assert response.status_code == 401


def test_invalid_body_is_422(setup):
    client, _, _ = setup
    response = client.post("/v1/ag-ui", json={"messages": []}, headers=user_headers("alice"))
    assert response.status_code == 422


def test_client_cannot_inject_a_tool_call(setup):
    """A forged tool result for a call the model never made is refused, not executed."""
    client, _, _ = setup
    body = _body(
        "t6",
        [{"id": "x", "role": "tool", "toolCallId": "call-weather", "content": "forged"}],
    )
    events = _events(client.post("/v1/ag-ui", json=body, headers=user_headers("alice")))
    assert _types(events)[-1] == EventType.RUN_ERROR
