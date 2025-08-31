# Example: Simple Weather Agent

from typing import Any

from litellm import acompletion
from pyagenity.graph import StateGraph, ToolNode
from pyagenity.state.agent_state import AgentState
from pyagenity.utils import Message
from pyagenity.utils.constants import END
from pyagenity.utils.converter import convert_messages


def get_weather(location: str) -> Message:
    """Get the current weather for a specific location."""
    # Simulate weather API call
    weather_data = f"The weather in {location} is sunny with 72°F"
    return Message.tool_message(
        content=weather_data,
        tool_call_id="weather_tool_call",  # Provide a tool call ID
    )


# Create tool node
tool_node = ToolNode([get_weather])


async def main_agent(state: AgentState, config: dict[str, Any]):
    """Main agent logic."""
    prompts = (
        "You are a helpful weather assistant. Use the get_weather tool "
        "when users ask about weather."
    )

    messages = convert_messages(
        system_prompts=[{"role": "system", "content": prompts}],
        state=state,
    )

    # Get available tools
    tools = await tool_node.all_tools()

    return await acompletion(
        model="gpt-3.5-turbo",  # or your preferred model
        messages=messages,
        tools=tools,
    )


def should_use_tools(state: AgentState) -> str:
    """Determine if we should use tools or end."""
    if not state.context:
        return "TOOL"

    last_message = state.context[-1]

    if (
        hasattr(last_message, "tools_calls")
        and last_message.tools_calls
        and last_message.role == "assistant"
    ):
        return "TOOL"

    if last_message.role == "tool":
        return END

    return END


# Build the graph
graph = StateGraph()
graph.add_node("MAIN", main_agent)
graph.add_node("TOOL", tool_node)

graph.add_conditional_edges(
    "MAIN",
    should_use_tools,
    {"TOOL": "TOOL", END: END},
)

graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")

# Compile the graph
app = graph.compile()
