"""
Graph-based React Agent Implementation

This module implements a reactive agent system using PyAgenity's StateGraph.
The agent can interact with tools (like weather checking) and maintain conversation
state through a checkpointer. The graph orchestrates the flow between the main
agent logic and tool execution.

Key Components:
- Weather tool: Demonstrates tool calling with dependency injection
- Main agent: AI-powered assistant that can use tools
- Graph flow: Conditional routing based on tool usage
- Checkpointer: Maintains conversation state across interactions

Architecture:
The system uses a state graph with two main nodes:
1. MAIN: Processes user input and generates AI responses
2. TOOL: Executes tool calls when requested by the AI

The graph conditionally routes between these nodes based on whether
the AI response contains tool calls. Conversation history is maintained
through the checkpointer, allowing for multi-turn conversations.

Tools are defined as functions with JSON schema docstrings that describe
their interface for the AI model. The ToolNode automatically extracts
these schemas for tool selection.

Dependencies:
- PyAgenity: For graph and state management
- LiteLLM: For AI model interactions
- InjectQ: For dependency injection
- Python logging: For debug and info messages
"""

import asyncio
import logging
from typing import Any

from dotenv import load_dotenv
from injectq import Inject
from litellm import acompletion
from pyagenity.checkpointer import InMemoryCheckpointer
from pyagenity.graph import StateGraph, ToolNode
from pyagenity.state.agent_state import AgentState
from pyagenity.utils import Message
from pyagenity.utils.callbacks import CallbackManager
from pyagenity.utils.constants import END
from pyagenity.utils.converter import convert_messages


# Configure logging for the module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Initialize in-memory checkpointer for maintaining conversation state
checkpointer = InMemoryCheckpointer()


"""
Note: The docstring below will be used as the tool description and it will be
passed to the AI model for tool selection, so keep it relevant and concise.
This function will be converted to a tool with the following schema:
[
        {
            'type': 'function',
            'function': {
                'name': 'get_weather',
                'description': 'Retrieve current weather information for a specified location.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string'}
                    },
                    'required': ['location']
                }
            }
        }
    ]

Parameters like tool_call_id, state, and checkpointer are injected automatically
by InjectQ when the tool is called by the agent.
Available injected parameters:
The following parameters are automatically injected by InjectQ when the tool is called,
but need to keep them as same name and type for proper injection:
- tool_call_id: Unique ID for the tool call
- state: Current AgentState containing conversation context
- config: Configuration dictionary passed during graph invocation

Below fields need to be used with Inject[] to get the instances:
- context_manager: ContextManager instance for managing context, like trimming
- publisher: Publisher instance for publishing events and logs
- checkpointer: InMemoryCheckpointer instance for state management
- store: InMemoryStore instance for temporary data storage
- callback: CallbackManager instance for handling callbacks

"""


def get_weather(
    location: str,
    tool_call_id: str,
    state: AgentState,
    checkpointer: InMemoryCheckpointer = Inject[InMemoryCheckpointer],
) -> Message:
    """Retrieve current weather information for a specified location."""
    # Demonstrate access to injected parameters
    logger.debug("***** Checkpointer instance: %s", checkpointer)
    if tool_call_id:
        logger.debug("Tool call ID: %s", tool_call_id)
    if state and hasattr(state, "context"):
        logger.debug("Number of messages in context: %d", len(state.context))

    # Mock weather response - in production, this would call a real weather API
    weather_info = f"The weather in {location} is sunny"
    return Message.tool_message(
        content=weather_info,
        tool_call_id=tool_call_id,
    )


# Create a tool node containing all available tools
tool_node = ToolNode([get_weather])


async def main_agent(
    state: AgentState,
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
    if (
        state.context
        and len(state.context) > 0
        and state.context[-1].role == "tool"
        and state.context[-1].tool_call_id is not None
    ):
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

    return response


def should_use_tools(state: AgentState) -> str:
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
    if last_message.role == "tool" and last_message.tool_call_id is not None:
        logger.info("Tool execution complete, ending conversation")
        return END

    # Default case: end conversation
    logger.debug("Default routing: ending conversation")
    return END


# Agent State
class CustomAgentState(AgentState):
    jd_text: str = ""  # Custom field for demonstration
    cv_text: str = ""  # Custom field for demonstration
    jd_id: int = 0  # Custom field for demonstration


# Initialize the state graph for orchestrating agent flow
graph = StateGraph[CustomAgentState](CustomAgentState())

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


async def check_tools():
    return await tool_node.all_tools()


if __name__ == "__main__":
    """
    Example usage of the compiled graph agent.

    This demonstrates how to invoke the agent with a user message
    that requests tool usage (weather information).
    """

    # Example input with a message requesting weather information
    input_data = {
        "messages": [Message.from_text("Please call the get_weather function for New York City")]
    }

    # Configuration for this conversation thread
    config = {"thread_id": "12345", "recursion_limit": 10}

    # Display graph structure for debugging
    logger.info("Graph Details:")
    logger.info(app.generate_graph())

    # Execute the graph with the input
    logger.info("Executing graph...")
    # result = app.invoke(input_data, config=config)

    # Display the final result
    # logger.info("Final response: %s", result)
    res = asyncio.run(check_tools())
    logger.info("Tools: %s", res)
