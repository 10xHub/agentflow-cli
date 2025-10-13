from agentflow.adapters.llm.model_response_converter import ModelResponseConverter
from agentflow.checkpointer import InMemoryCheckpointer
from agentflow.graph import StateGraph, ToolNode
from agentflow.state import AgentState
from agentflow.utils.constants import END
from agentflow.utils.converter import convert_messages
from dotenv import load_dotenv
from litellm import acompletion
from pydantic import Field


load_dotenv()

checkpointer = InMemoryCheckpointer()


class MyState(AgentState):
    jd_id: str = Field(default="default_jd_id", description="JD ID for the user")
    jd_text: str = Field(default="", description="JD Text for the user")
    cid: str = Field(default="default_cid", description="CID for the user")
    cv_text: str = Field(default="", description="CV Text for the user")


def get_weather(
    location: str,
    tool_call_id: str | None = None,
    state: AgentState | None = None,
) -> str:
    """
    Get the current weather for a specific location.
    This demo shows injectable parameters: tool_call_id and state are automatically injected.
    """
    # You can access injected parameters here
    if tool_call_id:
        print(f"Tool call ID: {tool_call_id}")  # noqa: T201
    if state and hasattr(state, "context"):
        print(f"Number of messages in context: {len(state.context)}")  # type: ignore  # noqa: T201

    return f"The weather in {location} is sunny"


tool_node = ToolNode([get_weather])


async def main_agent(
    state: AgentState,
):
    prompts = """
        You are a helpful assistant.
        Your task is to assist the user in finding information and answering questions.
    """

    messages = convert_messages(
        system_prompts=[
            {
                "role": "system",
                "content": prompts,
                "cache_control": {
                    "type": "ephemeral",
                    "ttl": "3600s",  # 👈 Cache for 1 hour
                },
            },
            {"role": "user", "content": "Today Date is 2024-06-15"},
        ],
        state=state,
    )

    mcp_tools = []

    # Check if the last message is a tool result - if so, make final response without tools
    if state.context and len(state.context) > 0 and state.context[-1].role == "tool":
        # Make final response without tools since we just got tool results
        response = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=messages,
        )
    else:
        # Regular response with tools available
        tools = await tool_node.all_tools()
        response = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=messages,
            tools=tools + mcp_tools,
        )

    return ModelResponseConverter(
        response,
        converter="litellm",
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


graph = StateGraph(state=MyState())
graph.add_node("MAIN", main_agent)
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
