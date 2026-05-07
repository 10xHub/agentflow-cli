from __future__ import annotations

from types import SimpleNamespace

from agentflow.core.state.message import Message
from agentflow.utils.constants import END

from graph.nodes.main_node import agent
from graph.utils.tool_decision import should_use_tools


def test_main_agent_is_configured_for_weather_assistant() -> None:
    assert agent.model == "gemini-3-flash-preview"
    assert agent.provider == "google"
    assert agent.trim_context is True
    assert agent.tool_node == "TOOL"

    system_prompt_text = " ".join(
        block["content"] for block in agent.system_prompt if "content" in block
    )
    assert "helpful assistant" in system_prompt_text.lower()


def test_should_end_when_no_context_exists() -> None:
    assert should_use_tools(SimpleNamespace(context=[])) == END


def test_should_route_assistant_tool_calls_to_tool_node() -> None:
    state = SimpleNamespace(
        context=[
            Message(
                role="assistant",
                content=[],
                tools_calls=[
                    {
                        "id": "call_1",
                        "name": "get_weather",
                        "args": {"location": "London"},
                    }
                ],
            )
        ]
    )

    assert should_use_tools(state) == "TOOL"


def test_should_route_tool_result_back_to_main_agent() -> None:
    state = SimpleNamespace(context=[Message(role="tool", content=[])])

    assert should_use_tools(state) == "MAIN"


def test_should_end_after_regular_assistant_response() -> None:
    state = SimpleNamespace(context=[Message(role="assistant", content=[])])

    assert should_use_tools(state) == END
