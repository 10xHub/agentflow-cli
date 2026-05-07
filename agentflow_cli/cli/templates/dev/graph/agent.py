import logging
import random
from datetime import datetime

from agentflow.core import Agent, StateGraph, ToolNode
from agentflow.core.state import AgentState
from agentflow.core.state.stream_emitter import StreamEmitter
from agentflow.storage.checkpointer import InMemoryCheckpointer
from agentflow.utils.constants import END
from dotenv import load_dotenv


load_dotenv()

checkpointer = InMemoryCheckpointer()

logger = logging.getLogger(__name__)


def call_weather_api(location: str) -> str:
    is_failed = random.choice([True, False])  # Randomly simulate success or failure  # noqa: S311
    if is_failed:
        raise Exception("Failed to fetch weather data due to a simulated API error.")
    return f"The weather in {location} is sunny"


def get_weather(
    location: str,
    tool_call_id: str | None = None,
    state: AgentState | None = None,
    emit: StreamEmitter | None = None,
) -> str:
    """
    Get the current weather for a specific location.
    This demo shows injectable parameters: tool_call_id and state are automatically injected.
    """
    # You can access injected parameters here
    if tool_call_id:
        logger.info(f"Tool call ID: {tool_call_id}")
    if state and hasattr(state, "context"):
        logger.info(f"Number of messages in context: {len(state.context)}")  # type: ignore
    if emit:
        emit.progress("Fetching weather data...")

    # return f"The weather in {location} is sunny"

    result = ""
    for i in range(3):  # Try up to 3 times
        try:
            result = call_weather_api(location)
            break  # If successful, exit the loop
        except Exception as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
            result = f"Sorry, I couldn't fetch the weather for {location} after multiple attempts."
            if emit:
                emit.progress(f"Attempt {i + 1} failed, retrying...")

    return result


tool_node = ToolNode(
    [
        get_weather,
    ]
)

# Create agent with tools
agent = Agent(
    model="gemini-3-flash-preview",
    provider="google",
    system_prompt=[
        {
            "role": "system",
            "content": """
                You are a helpful assistant.
                Your task is to assist the user in finding information and answering questions.
            """,
        },
        {
            "role": "user",
            "content": f"Today Date is {datetime.now().strftime('%Y-%m-%d')}",
        },  # Inject current date into system prompt
    ],
    trim_context=True,
    reasoning_config=True,
    tool_node=tool_node,
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
