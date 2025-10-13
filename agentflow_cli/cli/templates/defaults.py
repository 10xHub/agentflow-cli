"""Default templates for CLI initialization."""

from __future__ import annotations

import json
from typing import Final


# Default configuration template
DEFAULT_CONFIG_JSON: Final[str] = json.dumps(
    {
        "graphs": {
            "agent": "graph.react:app",
            "container": None,
        },
        "env": ".env",
        "auth": None,
        "thread_model_name": "gemini/gemini-2.0-flash",
        "generate_thread_name": False,
    },
    indent=2,
)

# Template for the default react agent graph
DEFAULT_REACT_PY: Final[str] = '''
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
from agentflowadapters.llm.model_response_converter import ModelResponseConverter
from agentflowcheckpointer import InMemoryCheckpointer
from agentflowgraph import StateGraph, ToolNode
from agentflowstate.agent_state import AgentState
from agentflowutils import Message
from agentflowutils.callbacks import CallbackManager
from agentflowutils.constants import END
from agentflowutils.converter import convert_messages


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
    return f"The weather in {location} is sunny"


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
    system_prompt = \"\"\"
        You are a helpful assistant.
        Your task is to assist the user in finding information and answering questions.
        You have access to various tools that can help you provide accurate information.
    \"\"\"

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

    return ModelResponseConverter(
        response,
        converter="litellm",
    )


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
    if last_message.role == "tool":
        logger.info("Tool execution complete, ending conversation")
        return END

    # Default case: end conversation
    logger.debug("Default routing: ending conversation")
    return END


# Initialize the state graph for orchestrating agent flow
graph = StateGraph()

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

'''

# Production templates (mirroring root repo tooling for convenience)
DEFAULT_PRE_COMMIT: Final[str] = """repos:
    - repo: https://github.com/pre-commit/pre-commit-hooks
        rev: v6.0.0
        hooks:
            - id: check-yaml
                exclude: ^(tests|docs|examples)/
            - id: trailing-whitespace
                exclude: ^(tests|docs|examples)/
            - id: check-added-large-files
                args: [--maxkb=100]
                exclude: ^(tests|docs|examples)/
            - id: check-ast
                exclude: ^(tests|docs|examples)/
            - id: check-builtin-literals
                exclude: ^(tests|docs|examples)/
            - id: check-case-conflict
                exclude: ^(tests|docs|examples)/
            - id: check-docstring-first
                exclude: ^(tests|docs|examples)/
            - id: check-merge-conflict
                exclude: ^(tests|docs|examples)/
            - id: debug-statements
                exclude: ^(tests|docs|examples)/
            - id: detect-private-key
                exclude: ^(tests|docs|examples)/

    - repo: https://github.com/asottile/pyupgrade
        rev: v3.17.0
        hooks:
            - id: pyupgrade
                args: [--py310-plus]
                exclude: ^(tests|docs|examples)/

    - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.5.7
        hooks:
            - id: ruff-format
                exclude: ^(tests|docs|examples)/

    - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.5.7
        hooks:
            - id: ruff
                args: [--fix, --exit-non-zero-on-fix]
                exclude: ^(tests|docs|examples)/

    - repo: https://github.com/PyCQA/bandit
        rev: 1.7.9
        hooks:
            - id: bandit
                args: [-c, pyproject.toml]
                additional_dependencies: ["bandit[toml]"]
                exclude: ^(tests|docs|examples)/
"""

DEFAULT_PYPROJECT: Final[str] = """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agentflow-cli-app"
version = "0.1.0"
description = "Pyagenity API application"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
        {name = "Your Name", email = "you@example.com"},
]
maintainers = [
        {name = "Your Name", email = "you@example.com"},
]
keywords = ["pyagenity", "api", "fastapi", "cli", "agentflow"]
classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
]
dependencies = [
        "agentflow-cli",
]

[project.scripts]
agentflow = "agentflow_cli.cli:main"

[tool.ruff]
line-length = 100
target-version = "py312"
lint.fixable = ["ALL"]
lint.select = [
    "E", "W", "F", "PL", "I", "B", "A", "S", "ISC", "ICN", "PIE", "Q",
    "RET", "SIM", "TID", "RUF", "YTT", "UP", "C4", "PTH", "G", "INP", "T20",
]
lint.ignore = [
    "UP006", "UP007", "RUF012", "G004", "B904", "B008", "ISC001",
]
lint.dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"
exclude = [
    "venv/*",
]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.per-file-ignores]
"bin/*.py" = ["E402", "S603", "T201", "S101"]
"*/tests/*.py" = ["E402", "S603", "T201", "S101"]
"*/test/*.py" = ["E402", "S603", "T201", "S101"]
"scripts/*.py" = ["E402", "S603", "T201", "S101", "INP001"]
"*/__init__.py" = ["E402", "S603", "T201", "S101"]
"*/migrations/*.py" = ["E402", "S603", "T201", "S101"]

[tool.ruff.lint.isort]
lines-after-imports = 2

[tool.ruff.lint.pylint]
max-args = 10

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = true

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.bandit]
exclude_dirs = ["*/tests/*", "*/agentflow_cli/tests/*"]
skips = ["B101", "B611", "B601", "B608"]

[tool.pytest.ini_options]
env = ["ENVIRONMENT=pytest"]
testpaths = ["tests"]
pythonpath = ["."]
filterwarnings = ["ignore::DeprecationWarning"]
addopts = [
    "--cov=agentflow_cli", "--cov-report=html", "--cov-report=term-missing",
    "--cov-report=xml", "--cov-fail-under=0", "--strict-markers", "-v"
]

[tool.coverage.run]
source = ["agentflow_cli"]
branch = true
omit = [
    "*/__init__.py", "*/tests/*", "*/migrations/*", "*/scripts/*", "*/venv/*", "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "if __name__ == '__main__':", "pragma: no cover", "@abc.abstractmethod", "@abstractmethod",
    "raise NotImplementedError",
]
show_missing = true

[tool.coverage.paths]
source = ["agentflow_cli", "*/site-packages/agentflow_cli"]

[tool.pytest-env]
ENVIRONMENT = "pytest"
"""


# Docker templates
def generate_dockerfile_content(
    python_version: str,
    port: int,
    requirements_file: str,
    has_requirements: bool,
    omit_cmd: bool = False,
) -> str:
    """Generate the content for the Dockerfile."""
    dockerfile_lines = [
        "# Dockerfile for Pyagenity API",
        "# Generated by agentflow-cli CLI",
        "",
        f"FROM python:{python_version}-slim",
        "",
        "# Set environment variables",
        "ENV PYTHONDONTWRITEBYTECODE=1",
        "ENV PYTHONUNBUFFERED=1",
        "ENV PYTHONPATH=/app",
        "",
        "# Set work directory",
        "WORKDIR /app",
        "",
        "# Install system dependencies",
        "RUN apt-get update \\",
        "    && apt-get install -y --no-install-recommends \\",
        "        build-essential \\",
        "        curl \\",
        "    && rm -rf /var/lib/apt/lists/*",
        "",
    ]

    if has_requirements:
        dockerfile_lines.extend(
            [
                "# Install Python dependencies",
                f"COPY {requirements_file} .",
                "RUN pip install --no-cache-dir --upgrade pip \\",
                f"    && pip install --no-cache-dir -r {requirements_file} \\",
                "    && pip install --no-cache-dir gunicorn uvicorn",
                "",
            ]
        )
    else:
        dockerfile_lines.extend(
            [
                "# Install agentflow-cli (since no requirements.txt found)",
                "RUN pip install --no-cache-dir --upgrade pip \\",
                "    && pip install --no-cache-dir agentflow-cli \\",
                "    && pip install --no-cache-dir gunicorn uvicorn",
                "",
            ]
        )

    dockerfile_lines.extend(
        [
            "# Copy application code",
            "COPY . .",
            "",
            "# Create a non-root user",
            "RUN groupadd -r appuser && useradd -r -g appuser appuser \\",
            "    && chown -R appuser:appuser /app",
            "USER appuser",
            "",
            "# Expose port",
            f"EXPOSE {port}",
            "",
            "# Health check",
            "HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\",
            f"    CMD curl -f http://localhost:{port}/ping || exit 1",
            "",
        ]
    )

    if not omit_cmd:
        dockerfile_lines.extend(
            [
                "# Run the application (production)",
                "# Use Gunicorn with Uvicorn workers for better performance and multi-core",
                "# utilization",
                (
                    'CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", '
                    f'"-b", "0.0.0.0:{port}", "agentflow_cli.src.app.main:app"]'
                ),
                "",
            ]
        )

    return "\n".join(dockerfile_lines)


def generate_docker_compose_content(service_name: str, port: int) -> str:
    """Generate a simple docker-compose.yml content for the API service."""
    return "\n".join(
        [
            "services:",
            f"  {service_name}:",
            "    build: .",
            "    image: agentflow-cli:latest",
            "    environment:",
            "      - PYTHONUNBUFFERED=1",
            "      - PYTHONDONTWRITEBYTECODE=1",
            "    ports:",
            f"      - '{port}:{port}'",
            (
                f"    command: [ 'gunicorn', '-k', 'uvicorn.workers.UvicornWorker', "
                f"'-b', '0.0.0.0:{port}', "
                "'agentflow_cli.src.app.main:app' ]"
            ),
            "    restart: unless-stopped",
            "    # Consider adding resource limits and deploy configurations in a swarm/stack",
            "    # deploy:",
            "    #   replicas: 2",
            "    #   resources:",
            "    #     limits:",
            "    #       cpus: '1.0'",
            "    #       memory: 512M",
        ]
    )
