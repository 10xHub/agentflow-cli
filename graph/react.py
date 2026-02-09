import logging
from time import sleep
from typing import Any

from agentflow.adapters.llm.model_response_converter import ModelResponseConverter
from agentflow.checkpointer import InMemoryCheckpointer
from agentflow.graph import StateGraph, ToolNode
from agentflow.state.agent_state import AgentState
from agentflow.utils.callbacks import CallbackManager
from agentflow.utils.constants import END
from agentflow.utils.converter import convert_messages
from dotenv import load_dotenv
from injectq import Inject
from litellm import acompletion


# Configure logging for the module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class MyAgentState(AgentState):
    cv_text: str = ""
    cid: str = ""
    jd_text: str = ""
    jd_id: str = ""


# Initialize in-memory checkpointer for maintaining conversation state
checkpointer = InMemoryCheckpointer[MyAgentState]()


def get_weather(
    location: str,
    tool_call_id: str,
    state: AgentState,
    checkpointer: InMemoryCheckpointer = Inject[InMemoryCheckpointer],
) -> str:
    """Retrieve current weather information for a specified location."""
    # Demonstrate access to injected parameters
    logger.debug("***** Checkpointer instance: %s", checkpointer)
    if tool_call_id:
        logger.debug("Tool call ID: %s", tool_call_id)
    if state and hasattr(state, "context"):
        logger.debug("Number of messages in context: %d", len(state.context))

    # Mock weather response - in production, this would call a real weather API
    sleep(1)  # Simulate network delay
    return f"The weather in {location} is sunny"


# Create a tool node containing all available tools
tool_node = ToolNode([get_weather])


async def main_agent(
    state: MyAgentState,
    config: dict,
    checkpointer: InMemoryCheckpointer = Inject[InMemoryCheckpointer],
    callback: CallbackManager = Inject[CallbackManager],
) -> Any:
    """
    Main agent logic that processes user messages and generates responses.

    This function implements the core AI agent behavior, handling both regular
    conversation and tool-augmented responses. It uses LiteLLM for AI completion
    and can access conversation history through the checkpointer.

    Args:
        state: Current agent state containing conversation context
        config: Configuration dictionary containing thread_id and other settings
        checkpointer: Checkpointer for retrieving conversation history (injected)
        callback: Callback manager for handling events (injected)

    Returns:
        dict: AI completion response containing the agent's reply

    The agent follows this logic:
    1. If the last message was a tool result, generate a final response without tools
    2. Otherwise, generate a response with available tools for potential tool usage
    """
    # System prompt defining the agent's role and capabilities
    system_prompt = """
        You are a helpful assistant.
        Your task is to assist the user in finding information and answering questions.
        You have access to various tools that can help you provide accurate information.
    """

    # Convert state messages to the format expected by the AI model
    messages = convert_messages(
        system_prompts=[{"role": "system", "content": system_prompt}],
        state=state,
    )

    # Retrieve conversation history from checkpointer
    try:
        thread_messages = await checkpointer.aget_thread({"thread_id": config["thread_id"]})
        logger.debug("Messages from checkpointer: %s", thread_messages)
    except Exception as e:
        logger.warning("Could not retrieve thread messages: %s", e)
        thread_messages = []

    # Log injected dependencies for debugging
    logger.debug("Checkpointer in main_agent: %s", checkpointer)
    logger.debug("CallbackManager in main_agent: %s", callback)

    # Placeholder for MCP (Model Context Protocol) tools
    # These would be additional tools from external sources
    mcp_tools = []
    is_stream = config.get("is_stream", False)

    # Determine response strategy based on conversation context
    if state.context and len(state.context) > 0 and state.context[-1].role == "tool":
        # Last message was a tool result - generate final response without tools
        logger.info("Generating final response after tool execution")
        response = await acompletion(
            model="gemini/gemini-2.0-flash-exp",  # Updated model name
            messages=messages,
            stream=is_stream,
        )
    else:
        # Regular response with tools available for potential usage
        logger.info("Generating response with tools available")
        tools = await tool_node.all_tools()
        response = await acompletion(
            model="gemini/gemini-2.0-flash-exp",  # Updated model name
            messages=messages,
            tools=tools + mcp_tools,
            stream=is_stream,
        )

    return ModelResponseConverter(
        response,
        converter="litellm",
    )


def should_use_tools(state: MyAgentState) -> str:
    """
    Determine the next step in the graph execution based on the current state.

    This routing function decides whether to continue with tool execution,
    end the conversation, or proceed with the main agent logic.

    Args:
        state: Current agent state containing the conversation context

    Returns:
        str: Next node to execute ("TOOL" or END constant)

    Routing Logic:
    - If last message is from assistant and contains tool calls -> "TOOL"
    - If last message is a tool result -> END (conversation complete)
    - Otherwise -> END (default fallback)
    """
    if not state.context or len(state.context) == 0:
        return END

    last_message = state.context[-1]
    if not last_message:
        return END

    # Check if assistant wants to use tools
    if (
        hasattr(last_message, "tools_calls")
        and last_message.tools_calls
        and len(last_message.tools_calls) > 0
        and last_message.role == "assistant"
    ):
        logger.debug("Routing to TOOL node for tool execution")
        return "TOOL"

    # Check if we just received tool results
    if last_message.role == "tool":
        logger.info("Tool execution complete, ending conversation")
        return END

    # Default case: end conversation
    logger.debug("Default routing: ending conversation")
    return END


# Initialize the state graph for orchestrating agent flow
graph = StateGraph[MyAgentState](MyAgentState())

# Add nodes to the graph
graph.add_node("MAIN", main_agent)  # Main agent processing node
graph.add_node("TOOL", tool_node)  # Tool execution node

# Define conditional edges from MAIN node
# Routes to TOOL if tools should be used, otherwise ends
graph.add_conditional_edges(
    "MAIN",
    should_use_tools,
    {"TOOL": "TOOL", END: END},
)

# Define edge from TOOL back to MAIN for continued conversation
graph.add_edge("TOOL", "MAIN")

# Set the entry point for graph execution
graph.set_entry_point("MAIN")

# Compile the graph with checkpointer for state management
app = graph.compile(
    checkpointer=checkpointer,
)
