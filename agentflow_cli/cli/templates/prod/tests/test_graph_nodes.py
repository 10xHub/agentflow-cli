from __future__ import annotations

from types import SimpleNamespace

from agentflow.core.state.message import Message
from agentflow.utils.constants import END

from graph.nodes.main_node import agent
from graph.state import FashionState
from graph.utils.tool_dicision import should_use_tools


def test_main_agent_is_configured_for_fashion_catalog_sales() -> None:
    assert agent.model == "gemini-2.5-flash"
    assert agent.provider == "google"
    assert agent.trim_context is True

    system_prompt = agent.system_prompt[0]["content"]
    assert "{company_name}" in system_prompt
    assert "{preferred_occasions}" in system_prompt
    assert "{user_preferences}" in system_prompt
    assert "product catalog" in system_prompt



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
                        "name": "search_catalog_products",
                        "args": {"text": "sari"},
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
