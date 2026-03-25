from dotenv import load_dotenv

from agentflow.checkpointer import InMemoryCheckpointer
from agentflow.graph import StateGraph, ToolNode
from agentflow.graph.agent import Agent
from agentflow.state import AgentState, ToolResult
from agentflow.utils.constants import END


load_dotenv()

checkpointer = InMemoryCheckpointer()


class CustomAgentState(AgentState):
    jd_name: str = "CustomAgentState"


def get_weather(
    location: str,
    tool_call_id: str | None = None,
    state: CustomAgentState | None = None,
) -> str:
    """
    Get the current weather for a specific location.
    This demo shows injectable parameters: tool_call_id and state are automatically injected.
    """
    # You can access injected parameters here
    if tool_call_id:
        print(f"Tool call ID: {tool_call_id}")
    if state and hasattr(state, "context"):
        print(f"Number of messages in context: {len(state.context)}")  # type: ignore

    return f"The weather in {location} is sunny"


def update_context(
    state: CustomAgentState,
    jd_name: str,
) -> ToolResult:
    """Update the current jd name in the state and report back to the AI."""
    return ToolResult(
        message=f"JD name has been updated to '{jd_name}'.",
        state={"jd_name": jd_name},
    )


tool_node = ToolNode(
    [
        get_weather,
        update_context,
    ]
)

# Create agent with tools
agent = Agent(
    model="gemini-2.5-flash",
    provider="google",
    system_prompt=[
        {
            "role": "system",
            "content": """
                You are a helpful assistant.
                Your task is to assist the user in finding information and answering questions.
            """,
        },
        {"role": "user", "content": "Today Date is 2024-06-15"},
    ],
    tool_node_name="TOOL",
    trim_context=True,
)


def should_use_tools(state: AgentState) -> str:
    """Determine if we should use tools or end the conversation."""
    if not state.context or len(state.context) == 0:
        return "TOOL"  # No context, might need tools

    last_message = state.context[-1]

    # If the last message is from assistant and has tool calls, go to TOOL
    if (
        hasattr(last_message, "tools_calls")
        and last_message.tools_calls
        and len(last_message.tools_calls) > 0
        and last_message.role == "assistant"
    ):
        return "TOOL"

    # If last message is a tool result, we should be done (AI will make final response)
    if last_message.role == "tool":
        return "MAIN"

    # Default to END for other cases
    return END


graph = StateGraph()
graph.add_node("MAIN", agent)
graph.add_node("TOOL", tool_node)

# Add conditional edges from MAIN
graph.add_conditional_edges(
    "MAIN",
    should_use_tools,
    {"TOOL": "TOOL", END: END},
)

# Always go back to MAIN after TOOL execution
graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")


app = graph.compile(
    checkpointer=checkpointer,
)