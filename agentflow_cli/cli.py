# """
# Pyagenity CLI - Backward compatibility wrapper and utility functions.

# This module provides backward compatibility with the old CLI interface
# while delegating to the new modular architecture.
# """

# from __future__ import annotations

# import json
# import logging
# import os
# import sys
# import tomllib
# from pathlib import Path
# from typing import Any

# import typer
# import uvicorn
# from dotenv import load_dotenv

# # Backward compatibility imports remain in place

# # Keep the original functions for backward compatibility

# # Maintain backward compatibility for imports
# try:
#     import importlib.resources

#     HAS_IMPORTLIB_RESOURCES = True
# except ImportError:
#     importlib = None  # type: ignore
#     HAS_IMPORTLIB_RESOURCES = False


# # Legacy output functions for backward compatibility
# def _em(fmt: str) -> str:
#     """Return formatted text with a small emoji prefix for emphasis."""
#     return f"✨  {fmt}"


# def _success(msg: str) -> None:
#     """Legacy success message function."""
#     typer.echo(f"\n\033[92m{_em(msg)}\033[0m")


# def _info(msg: str) -> None:
#     """Legacy info message function."""
#     typer.echo(f"\n\033[94m{_em(msg)}\033[0m")


# def _error(msg: str) -> None:
#     """Legacy error message function."""
#     typer.echo(f"\n\033[91m⚠️  {msg}\033[0m", err=True)


# def _read_package_version(pyproject_path: Path) -> str:
#     try:
#         with pyproject_path.open("rb") as f:
#             data = tomllib.load(f)
#         return data.get("project", {}).get("version", "unknown")
#     except Exception:
#         return "unknown"


# def _print_banner(title: str, subtitle: str, color: str = "cyan") -> None:
#     """Print a small colored ASCII banner with a title and subtitle.

#     color: one of 'red','green','yellow','blue','magenta','cyan','white'
#     """
#     colors = {
#         "red": "\033[91m",
#         "green": "\033[92m",
#         "yellow": "\033[93m",
#         "blue": "\033[94m",
#         "magenta": "\033[95m",
#         "cyan": "\033[96m",
#         "white": "\033[97m",
#     }
#     c = colors.get(color, colors["cyan"])
#     reset = "\033[0m"
#     typer.echo("")
#     typer.echo(c + f"== {title} ==" + reset)
#     typer.echo(f"{subtitle}")
#     typer.echo("")


# load_dotenv()

# # Basic logging setup
# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# app = typer.Typer()


# def find_config_file(config_path: str) -> str:
#     """
#     Find the config file in the following order:
#     1. Absolute path if provided
#     2. Relative to current working directory
#     3. In the package installation directory (fallback)
#     """
#     config_path_obj = Path(config_path)

#     # If absolute path is provided, use it directly
#     if config_path_obj.is_absolute():
#         if not config_path_obj.exists():
#             _error(f"Config file not found at {config_path}")
#             raise typer.Exit(1)
#         return str(config_path_obj)

#     # Check if file exists in current working directory
#     cwd_config = Path.cwd() / config_path
#     if cwd_config.exists():
#         return str(cwd_config)

#     # Check if file exists relative to the script location (for development)
#     script_dir = Path(__file__).parent
#     script_config = script_dir / config_path
#     if script_config.exists():
#         return str(script_config)

#     # Try to find in package data (when installed)
#     if HAS_IMPORTLIB_RESOURCES and importlib:
#         try:
#             # Try to find the config in the package
#             files = importlib.resources.files("agentflow_cli")
#             if files:
#                 package_config = files / config_path
#                 # Check if the file exists by trying to read it
#                 try:
#                     package_config.read_text()
#                     return str(package_config)
#                 except (FileNotFoundError, OSError):
#                     pass
#         except (ImportError, AttributeError):
#             pass

#     # If still not found, suggest creating one
#     _error(f"Config file '{config_path}' not found in:")
#     typer.echo(f"  - {cwd_config}")
#     typer.echo(f"  - {script_config}")
#     typer.echo("")
#     _error("Please ensure the config file exists or provide an absolute path.")
#     raise typer.Exit(1)


# @app.command()
# def api(
#     config: str = typer.Option("pyagenity.json", help="Path to config file"),
#     host: str = typer.Option(
#         "0.0.0.0",  # Binding to all interfaces for server
#         help="Host to run the API on (default: 0.0.0.0, binds to all interfaces;"
#         " use 127.0.0.1 for localhost only)",
#     ),
#     port: int = typer.Option(8000, help="Port to run the API on"),
#     reload: bool = typer.Option(True, help="Enable auto-reload"),
# ):
#     """Start the Pyagenity API server."""
#     _print_banner(
#         "API (development)",
#         "Starting development server via Uvicorn. Not for production use.",
#     )
#     # Find the actual config file path
#     actual_config_path = find_config_file(config)

#     logging.info(f"Starting API with config: {actual_config_path}, host: {host}, port: {port}")
#     os.environ["GRAPH_PATH"] = actual_config_path

#     # Ensure we're using the correct module path
#     sys.path.insert(0, str(Path(__file__).parent))

#     uvicorn.run("agentflow_cli.src.app.main:app", host=host, port=port, reload=reload, workers=1)


# @app.command()
# def version():
#     """Show the CLI version."""
#     # CLI version hardcoded, package version read from pyproject.toml
#     _print_banner(
#         "Version",
#         "Show pyagenity CLI and package version info",
#         color="green",
#     )
#     cli_version = "1.0.0"
#     project_root = Path(__file__).resolve().parents[1]
#     pkg_version = _read_package_version(project_root / "pyproject.toml")

#     _success(f"pyagenity-api CLI\n  Version: {cli_version}")
#     _info(f"pyagenity-api Package\n  Version: {pkg_version}")


# def _write_file(path: Path, content: str, *, force: bool) -> None:
#     """Write content to path, creating parents. Respect force flag."""
#     path.parent.mkdir(parents=True, exist_ok=True)
#     if path.exists() and not force:
#         _error(f"File already exists: {path}. Use --force to overwrite.")
#         raise typer.Exit(1)
#     path.write_text(content, encoding="utf-8")


# DEFAULT_CONFIG_JSON = json.dumps(
#     {
#         "graphs": {
#             "agent": "graph.react:app",
#             "container": None,
#         },
#         "env": ".env",
#         "auth": None,
#         "thread_model_name": "gemini/gemini-2.0-flash",
#         "generate_thread_name": False,
#     },
#     indent=2,
# )


# # Template for the default react agent graph
# DEFAULT_REACT_PY = '''
# """
# Graph-based React Agent Implementation

# This module implements a reactive agent system using PyAgenity's StateGraph.
# The agent can interact with tools (like weather checking) and maintain conversation
# state through a checkpointer. The graph orchestrates the flow between the main
# agent logic and tool execution.

# Key Components:
# - Weather tool: Demonstrates tool calling with dependency injection
# - Main agent: AI-powered assistant that can use tools
# - Graph flow: Conditional routing based on tool usage
# - Checkpointer: Maintains conversation state across interactions

# Architecture:
# The system uses a state graph with two main nodes:
# 1. MAIN: Processes user input and generates AI responses
# 2. TOOL: Executes tool calls when requested by the AI

# The graph conditionally routes between these nodes based on whether
# the AI response contains tool calls. Conversation history is maintained
# through the checkpointer, allowing for multi-turn conversations.

# Tools are defined as functions with JSON schema docstrings that describe
# their interface for the AI model. The ToolNode automatically extracts
# these schemas for tool selection.

# Dependencies:
# - PyAgenity: For graph and state management
# - LiteLLM: For AI model interactions
# - InjectQ: For dependency injection
# - Python logging: For debug and info messages
# """

# import asyncio
# import logging
# from typing import Any

# from dotenv import load_dotenv
# from injectq import Inject
# from litellm import acompletion
# from pyagenity.adapters.llm.model_response_converter import ModelResponseConverter
# from pyagenity.checkpointer import InMemoryCheckpointer
# from pyagenity.graph import StateGraph, ToolNode
# from pyagenity.state.agent_state import AgentState
# from pyagenity.utils import Message
# from pyagenity.utils.callbacks import CallbackManager
# from pyagenity.utils.constants import END
# from pyagenity.utils.converter import convert_messages


# # Configure logging for the module
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler()],
# )
# logger = logging.getLogger(__name__)

# # Load environment variables from .env file
# load_dotenv()

# # Initialize in-memory checkpointer for maintaining conversation state
# checkpointer = InMemoryCheckpointer()


# """
# Note: The docstring below will be used as the tool description and it will be
# passed to the AI model for tool selection, so keep it relevant and concise.
# This function will be converted to a tool with the following schema:
# [
#         {
#             'type': 'function',
#             'function': {
#                 'name': 'get_weather',
#                 'description': 'Retrieve current weather information for a specified location.',
#                 'parameters': {
#                     'type': 'object',
#                     'properties': {
#                         'location': {'type': 'string'}
#                     },
#                     'required': ['location']
#                 }
#             }
#         }
#     ]

# Parameters like tool_call_id, state, and checkpointer are injected automatically
# by InjectQ when the tool is called by the agent.
# Available injected parameters:
# The following parameters are automatically injected by InjectQ when the tool is called,
# but need to keep them as same name and type for proper injection:
# - tool_call_id: Unique ID for the tool call
# - state: Current AgentState containing conversation context
# - config: Configuration dictionary passed during graph invocation

# Below fields need to be used with Inject[] to get the instances:
# - context_manager: ContextManager instance for managing context, like trimming
# - publisher: Publisher instance for publishing events and logs
# - checkpointer: InMemoryCheckpointer instance for state management
# - store: InMemoryStore instance for temporary data storage
# - callback: CallbackManager instance for handling callbacks

# """


# def get_weather(
#     location: str,
#     tool_call_id: str,
#     state: AgentState,
#     checkpointer: InMemoryCheckpointer = Inject[InMemoryCheckpointer],
# ) -> Message:
#     """Retrieve current weather information for a specified location."""
#     # Demonstrate access to injected parameters
#     logger.debug("***** Checkpointer instance: %s", checkpointer)
#     if tool_call_id:
#         logger.debug("Tool call ID: %s", tool_call_id)
#     if state and hasattr(state, "context"):
#         logger.debug("Number of messages in context: %d", len(state.context))

#     # Mock weather response - in production, this would call a real weather API
#     return f"The weather in {location} is sunny"


# # Create a tool node containing all available tools
# tool_node = ToolNode([get_weather])


# async def main_agent(
#     state: AgentState,
#     config: dict,
#     checkpointer: InMemoryCheckpointer = Inject[InMemoryCheckpointer],
#     callback: CallbackManager = Inject[CallbackManager],
# ) -> Any:
#     """
#     Main agent logic that processes user messages and generates responses.

#     This function implements the core AI agent behavior, handling both regular
#     conversation and tool-augmented responses. It uses LiteLLM for AI completion
#     and can access conversation history through the checkpointer.

#     Args:
#         state: Current agent state containing conversation context
#         config: Configuration dictionary containing thread_id and other settings
#         checkpointer: Checkpointer for retrieving conversation history (injected)
#         callback: Callback manager for handling events (injected)

#     Returns:
#         dict: AI completion response containing the agent's reply

#     The agent follows this logic:
#     1. If the last message was a tool result, generate a final response without tools
#     2. Otherwise, generate a response with available tools for potential tool usage
#     """
#     # System prompt defining the agent's role and capabilities
#     system_prompt = """
#         You are a helpful assistant.
#         Your task is to assist the user in finding information and answering questions.
#         You have access to various tools that can help you provide accurate information.
#     """

#     # Convert state messages to the format expected by the AI model
#     messages = convert_messages(
#         system_prompts=[{"role": "system", "content": system_prompt}],
#         state=state,
#     )

#     # Retrieve conversation history from checkpointer
#     try:
#         thread_messages = await checkpointer.aget_thread({"thread_id": config["thread_id"]})
#         logger.debug("Messages from checkpointer: %s", thread_messages)
#     except Exception as e:
#         logger.warning("Could not retrieve thread messages: %s", e)
#         thread_messages = []

#     # Log injected dependencies for debugging
#     logger.debug("Checkpointer in main_agent: %s", checkpointer)
#     logger.debug("CallbackManager in main_agent: %s", callback)

#     # Placeholder for MCP (Model Context Protocol) tools
#     # These would be additional tools from external sources
#     mcp_tools = []
#     is_stream = config.get("is_stream", False)

#     # Determine response strategy based on conversation context
#     if (
#         state.context
#         and len(state.context) > 0
#         and state.context[-1].role == "tool"
#         and state.context[-1].tool_call_id is not None
#     ):
#         # Last message was a tool result - generate final response without tools
#         logger.info("Generating final response after tool execution")
#         response = await acompletion(
#             model="gemini/gemini-2.0-flash-exp",  # Updated model name
#             messages=messages,
#             stream=is_stream,
#         )
#     else:
#         # Regular response with tools available for potential usage
#         logger.info("Generating response with tools available")
#         tools = await tool_node.all_tools()
#         response = await acompletion(
#             model="gemini/gemini-2.0-flash-exp",  # Updated model name
#             messages=messages,
#             tools=tools + mcp_tools,
#             stream=is_stream,
#         )

#     return ModelResponseConverter(
#         response,
#         converter="litellm",
#     )


# def should_use_tools(state: AgentState) -> str:
#     """
#     Determine the next step in the graph execution based on the current state.

#     This routing function decides whether to continue with tool execution,
#     end the conversation, or proceed with the main agent logic.

#     Args:
#         state: Current agent state containing the conversation context

#     Returns:
#         str: Next node to execute ("TOOL" or END constant)

#     Routing Logic:
#     - If last message is from assistant and contains tool calls -> "TOOL"
#     - If last message is a tool result -> END (conversation complete)
#     - Otherwise -> END (default fallback)
#     """
#     if not state.context or len(state.context) == 0:
#         return END

#     last_message = state.context[-1]
#     if not last_message:
#         return END

#     # Check if assistant wants to use tools
#     if (
#         hasattr(last_message, "tools_calls")
#         and last_message.tools_calls
#         and len(last_message.tools_calls) > 0
#         and last_message.role == "assistant"
#     ):
#         logger.debug("Routing to TOOL node for tool execution")
#         return "TOOL"

#     # Check if we just received tool results
#     if last_message.role == "tool":
#         logger.info("Tool execution complete, ending conversation")
#         return END

#     # Default case: end conversation
#     logger.debug("Default routing: ending conversation")
#     return END


# # Initialize the state graph for orchestrating agent flow
# graph = StateGraph()

# # Add nodes to the graph
# graph.add_node("MAIN", main_agent)  # Main agent processing node
# graph.add_node("TOOL", tool_node)  # Tool execution node

# # Define conditional edges from MAIN node
# # Routes to TOOL if tools should be used, otherwise ends
# graph.add_conditional_edges(
#     "MAIN",
#     should_use_tools,
#     {"TOOL": "TOOL", END: END},
# )

# # Define edge from TOOL back to MAIN for continued conversation
# graph.add_edge("TOOL", "MAIN")

# # Set the entry point for graph execution
# graph.set_entry_point("MAIN")

# # Compile the graph with checkpointer for state management
# app = graph.compile(
#     checkpointer=checkpointer,
# )


# async def check_tools():
#     return await tool_node.all_tools()


# if __name__ == "__main__":
#     """
#     Example usage of the compiled graph agent.

#     This demonstrates how to invoke the agent with a user message
#     that requests tool usage (weather information).
#     """

#     # Example input with a message requesting weather information
#     input_data = {
#         "messages": [Message.from_text("Please call the get_weather function for New York City")]
#     }

#     # Configuration for this conversation thread
#     config = {"thread_id": "12345", "recursion_limit": 10}

#     # Display graph structure for debugging
#     logger.info("Graph Details:")
#     logger.info(app.generate_graph())

#     # Execute the graph with the input
#     logger.info("Executing graph...")
#     # result = app.invoke(input_data, config=config)

#     # Display the final result
#     # logger.info("Final response: %s", result)
#     res = asyncio.run(check_tools())
#     logger.info("Tools: %s", res)
# '''


# @app.command()
# def init(
#     path: str = typer.Option(".", help="Directory to initialize config and graph files in"),
#     force: bool = typer.Option(False, help="Overwrite existing files if they exist"),
# ):
#     """Initialize default config and graph files (pyagenity.json and graph/react.py)."""
#     _print_banner(
#         "Init",
#         "Create pyagenity.json and graph/react.py scaffold files",
#         color="magenta",
#     )
#     # Write config JSON
#     config_path = Path(path) / "pyagenity.json"
#     _write_file(config_path, DEFAULT_CONFIG_JSON + "\n", force=force)

#     # Write graph/react.py
#     react_path = Path(path) / "graph/react.py"
#     _write_file(react_path, DEFAULT_REACT_PY, force=force)

#     # Write __init__.py to make graph a package
#     init_path = react_path.parent / "__init__.py"
#     _write_file(init_path, "", force=force)

#     _success(f"Created config file at {config_path}")
#     _success(f"Created react graph at {react_path}")
#     _info("You can now run: pag api")


# @app.command()
# def build(
#     output: str = typer.Option("Dockerfile", help="Output Dockerfile path"),
#     force: bool = typer.Option(False, help="Overwrite existing Dockerfile"),
#     python_version: str = typer.Option("3.13", help="Python version to use"),
#     port: int = typer.Option(8000, help="Port to expose in the container"),
#     docker_compose: bool = typer.Option(
#         False,
#         "--docker-compose/--no-docker-compose",
#         help="Also generate docker-compose.yml and omit CMD in Dockerfile",
#     ),
#     service_name: str = typer.Option(
#         "pyagenity-api",
#         help="Service name to use in docker-compose.yml (if generated)",
#     ),
# ):
#     """Generate a Dockerfile for the Pyagenity API application."""
#     _print_banner(
#         "Build",
#         "Generate Dockerfile (and optional docker-compose.yml) for production image",
#         color="yellow",
#     )
#     output_path = Path(output)
#     current_dir = Path.cwd()

#     # Check if Dockerfile already exists
#     if output_path.exists() and not force:
#         _error(f"Dockerfile already exists at {output_path}")
#         _info("Use --force to overwrite")
#         raise typer.Exit(1)

#     # Discover requirements files and pick one
#     requirements_files, requirements_file = _discover_requirements(current_dir)

#     # Generate Dockerfile content
#     dockerfile_content = generate_dockerfile_content(
#         python_version=python_version,
#         port=port,
#         requirements_file=requirements_file,
#         has_requirements=bool(requirements_files),
#         omit_cmd=docker_compose,
#     )

#     # Write Dockerfile and optional compose
#     try:
#         output_path.write_text(dockerfile_content, encoding="utf-8")
#         typer.echo(f"✅ Successfully generated Dockerfile at {output_path}")

#         if requirements_files:
#             typer.echo(f"📦 Using requirements file: {requirements_files[0]}")

#         if docker_compose:
#             _write_docker_compose(force=force, service_name=service_name, port=port)

#         typer.echo("\n🚀 Next steps:")
#         step1_suffix = " and docker-compose.yml" if docker_compose else ""
#         typer.echo("1. Review the generated Dockerfile" + step1_suffix)
#         typer.echo("2. Build the Docker image: docker build -t pyagenity-api .")
#         if docker_compose:
#             typer.echo("3. Run with compose: docker compose up")
#         else:
#             typer.echo("3. Run the container: docker run -p 8000:8000 pyagenity-api")

#     except Exception as e:
#         typer.echo(f"Error writing Dockerfile: {e}", err=True)
#         raise typer.Exit(1)


# def generate_dockerfile_content(
#     python_version: str,
#     port: int,
#     requirements_file: str,
#     has_requirements: bool,
#     omit_cmd: bool = False,
# ) -> str:
#     """Generate the content for the Dockerfile."""
#     dockerfile_lines = [
#         "# Dockerfile for Pyagenity API",
#         "# Generated by pyagenity-api CLI",
#         "",
#         f"FROM python:{python_version}-slim",
#         "",
#         "# Set environment variables",
#         "ENV PYTHONDONTWRITEBYTECODE=1",
#         "ENV PYTHONUNBUFFERED=1",
#         "ENV PYTHONPATH=/app",
#         "",
#         "# Set work directory",
#         "WORKDIR /app",
#         "",
#         "# Install system dependencies",
#         "RUN apt-get update \\",
#         "    && apt-get install -y --no-install-recommends \\",
#         "        build-essential \\",
#         "        curl \\",
#         "    && rm -rf /var/lib/apt/lists/*",
#         "",
#     ]

#     if has_requirements:
#         dockerfile_lines.extend(
#             [
#                 "# Install Python dependencies",
#                 f"COPY {requirements_file} .",
#                 "RUN pip install --no-cache-dir --upgrade pip \\",
#                 f"    && pip install --no-cache-dir -r {requirements_file} \\",
#                 "    && pip install --no-cache-dir gunicorn uvicorn",
#                 "",
#             ]
#         )
#     else:
#         dockerfile_lines.extend(
#             [
#                 "# Install pyagenity-api (since no requirements.txt found)",
#                 "RUN pip install --no-cache-dir --upgrade pip \\",
#                 "    && pip install --no-cache-dir pyagenity-api \\",
#                 "    && pip install --no-cache-dir gunicorn uvicorn",
#                 "",
#             ]
#         )

#     dockerfile_lines.extend(
#         [
#             "# Copy application code",
#             "COPY . .",
#             "",
#             "# Create a non-root user",
#             "RUN groupadd -r appuser && useradd -r -g appuser appuser \\",
#             "    && chown -R appuser:appuser /app",
#             "USER appuser",
#             "",
#             "# Expose port",
#             f"EXPOSE {port}",
#             "",
#             "# Health check",
#             "HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\",
#             f"    CMD curl -f http://localhost:{port}/ping || exit 1",
#             "",
#         ]
#     )

#     if not omit_cmd:
#         dockerfile_lines.extend(
#             [
#                 "# Run the application (production)",
#                 "# Use Gunicorn with Uvicorn workers for better performance and multi-core",
#                 "# utilization",
#                 (
#                     'CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", '
#                     f'"-b", "0.0.0.0:{port}", "agentflow_cli.src.app.main:app"]'
#                 ),
#                 "",
#             ]
#         )

#     return "\n".join(dockerfile_lines)


# def generate_docker_compose_content(service_name: str, port: int) -> str:
#     """Generate a simple docker-compose.yml content for the API service."""
#     return "\n".join(
#         [
#             "services:",
#             f"  {service_name}:",
#             "    build: .",
#             "    image: pyagenity-api:latest",
#             "    environment:",
#             "      - PYTHONUNBUFFERED=1",
#             "      - PYTHONDONTWRITEBYTECODE=1",
#             "    ports:",
#             f"      - '{port}:{port}'",
#             (
#                 f"    command: [ 'gunicorn', '-k', 'uvicorn.workers.UvicornWorker', "
#                 f"'-b', '0.0.0.0:{port}', "
#                 "'agentflow_cli.src.app.main:app' ]"
#             ),
#             "    restart: unless-stopped",
#             "    # Consider adding resource limits and deploy configurations in a swarm/stack",
#             "    # deploy:",
#             "    #   replicas: 2",
#             "    #   resources:",
#             "    #     limits:",
#             "    #       cpus: '1.0'",
#             "    #       memory: 512M",
#         ]
#     )


# def _discover_requirements(current_dir: Path):
#     """Find requirement files and pick the first one to install.

#     Returns a tuple of (found_files_list, chosen_filename_str).
#     """
#     requirements_files = []
#     requirements_paths = [
#         current_dir / "requirements.txt",
#         current_dir / "requirements" / "requirements.txt",
#         current_dir / "requirements" / "base.txt",
#         current_dir / "requirements" / "production.txt",
#     ]

#     for req_path in requirements_paths:
#         if req_path.exists():
#             requirements_files.append(req_path)

#     if not requirements_files:
#         _error("No requirements.txt file found!")
#         _info("Searched in the following locations:")
#         for req_path in requirements_paths:
#             typer.echo(f"  - {req_path}")
#         typer.echo("")
#         _info("Consider creating a requirements.txt file with your dependencies.")

#         # Ask user if they want to continue
#         if not typer.confirm("Continue generating Dockerfile without requirements.txt?"):
#             raise typer.Exit(0)

#     requirements_file = "requirements.txt"
#     if requirements_files:
#         requirements_file = requirements_files[0].name
#         if len(requirements_files) > 1:
#             _info(f"Found multiple requirements files, using: {requirements_file}")

#     return requirements_files, requirements_file


# def _write_docker_compose(*, force: bool, service_name: str, port: int) -> None:
#     """Write docker-compose.yml with the provided parameters."""
#     compose_path = Path("docker-compose.yml")
#     if compose_path.exists() and not force:
#         _error(f"docker-compose.yml already exists at {compose_path}. Use --force to overwrite.")
#         raise typer.Exit(1)
#     compose_content = generate_docker_compose_content(service_name=service_name, port=port)
#     compose_path.write_text(compose_content, encoding="utf-8")
#     _success(f"Generated docker-compose file at {compose_path}")


# def main() -> None:
#     """Main entry point for the CLI.

#     This function now delegates to the new modular CLI architecture
#     while maintaining backward compatibility.
#     """
#     # Delegate to the new main CLI
#     from agentflow_cli.cli.main import main as new_main

#     new_main()


# if __name__ == "__main__":
#     main()
