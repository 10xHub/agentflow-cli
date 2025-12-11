from collections import defaultdict
from collections.abc import AsyncIterable
from typing import Any
from uuid import uuid4

from agentflow.checkpointer import BaseCheckpointer
from agentflow.graph import CompiledGraph
from agentflow.state import AgentState, Message, StreamChunk, StreamEvent
from agentflow.utils.thread_info import ThreadInfo
from fastapi import HTTPException
from injectq import InjectQ, inject, singleton
from pydantic import BaseModel

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    GraphSetupSchema,
)
from agentflow_cli.src.app.utils import DummyThreadNameGenerator, ThreadNameGenerator


@singleton
class GraphService:
    """
    Service class for graph-related operations.

    This class acts as an intermediary between the controllers and the
    CompiledGraph, facilitating graph execution operations.
    """

    @inject
    def __init__(
        self,
        graph: CompiledGraph,
        checkpointer: BaseCheckpointer,
        config: GraphConfig,
        thread_name_generator: ThreadNameGenerator | None = None,
    ):
        """
        Initializes the GraphService with a CompiledGraph instance.

        Args:
            graph (CompiledGraph): An instance of CompiledGraph for
                                   graph execution operations.
        """
        self._graph = graph
        self.config = config
        self.checkpointer = checkpointer
        self.thread_name_generator = thread_name_generator

    async def _save_thread_name(
        self,
        config: dict[str, Any],
        thread_id: int,
        messages: list[str],
    ) -> str:
        """
        Save the generated thread name to the database.
        """
        if not self.thread_name_generator:
            thread_name = await DummyThreadNameGenerator().generate_name([])
            logger.debug("No thread name generator configured, using dummy thread name generator.")
            return thread_name

        thread_name = await self.thread_name_generator.generate_name(messages)

        res = await self.checkpointer.aput_thread(
            config,
            ThreadInfo(thread_id=thread_id, thread_name=thread_name),
        )
        if res:
            logger.info(f"Generated thread name: {thread_name} for thread_id: {thread_id}")

        return thread_name

    async def _save_thread(self, config: dict[str, Any], thread_id: int):
        """
        Save the generated thread name to the database.
        """
        return await self.checkpointer.aput_thread(
            config,
            ThreadInfo(thread_id=thread_id),
        )

    def _extract_context_info(
        self, raw_state, result: dict[str, Any]
    ) -> tuple[list[Message] | None, str | None]:
        """Extract context and context_summary from result or state."""
        context: list[Message] | None = result.get("context")
        context_summary: str | None = result.get("context_summary")

        # If not found, try reading from state (supports both dict and model)
        if not context_summary and raw_state is not None:
            try:
                if isinstance(raw_state, dict):
                    context_summary = raw_state.get("context_summary")
                else:
                    context_summary = getattr(raw_state, "context_summary", None)
            except Exception:
                context_summary = None

        if not context and raw_state is not None:
            try:
                if isinstance(raw_state, dict):
                    context = raw_state.get("context")
                else:
                    context = getattr(raw_state, "context", None)
            except Exception:
                context = None

        return context, context_summary

    async def stop_graph(
        self,
        thread_id: str,
        user: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Stop the graph execution for a specific thread.

        Args:
            thread_id (str): The thread ID to stop
            user (dict): User information for context
            config (dict, optional): Additional configuration for the stop operation

        Returns:
            dict: Stop result with status information

        Raises:
            HTTPException: If stop operation fails or user doesn't have permission.
        """
        try:
            logger.info(f"Stopping graph execution for thread: {thread_id}")
            logger.debug(f"User info: {user}")

            # Prepare config with thread_id and user info
            stop_config = {
                "thread_id": thread_id,
                "user": user,
            }

            # Merge additional config if provided
            if config:
                stop_config.update(config)

            # Call the graph's astop method
            result = await self._graph.astop(stop_config)

            logger.info(f"Graph stop completed for thread {thread_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Graph stop failed for thread {thread_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Graph stop failed for thread {thread_id}: {e!s}"
            )

    async def _prepare_input(
        self,
        graph_input: GraphInputSchema,
    ):
        is_new_thread = False
        config = graph_input.config or {}
        if "thread_id" in config:
            thread_id = config["thread_id"]
        else:
            thread_id = await InjectQ.get_instance().atry_get("generated_id") or str(uuid4())
            is_new_thread = True

        # update thread id
        config["thread_id"] = str(thread_id)

        # check recursion limit set or not
        config["recursion_limit"] = graph_input.recursion_limit or 25

        # Prepare the input for the graph
        input_data: dict = {
            "messages": graph_input.messages,
        }
        if graph_input.initial_state:
            input_data["state"] = graph_input.initial_state

        return (
            input_data,
            config,
            {
                "is_new_thread": is_new_thread,
                "thread_id": str(thread_id),
            },
        )

    async def invoke_graph(
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
    ) -> GraphInvokeOutputSchema:
        """
        Invokes the graph with the provided input and returns the final result.

        Args:
            graph_input (GraphInputSchema): The input data for graph execution.

        Returns:
            GraphInvokeOutputSchema: The final result from graph execution.

        Raises:
            HTTPException: If graph execution fails.
        """
        try:
            logger.debug(f"Invoking graph with input: {graph_input.messages}")

            # Prepare the input
            input_data, config, meta = await self._prepare_input(graph_input)
            # add user inside config
            config["user"] = user
            config["user_id"] = user.get("user_id", "anonymous")

            # Try to save thread info in the db even for existing threads
            # this will help in updating last accessed time
            # and get is thread newly created or not, this way it's consistent
            is_new_thread = await self._save_thread(config, config["thread_id"])
            if is_new_thread and type(is_new_thread) is bool:
                meta["is_new_thread"] = True

            # Execute the graph
            result = await self._graph.ainvoke(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            )

            logger.info("Graph execution completed successfully")

            # Extract messages and state from result
            messages: list[Message] = result.get("messages", [])
            raw_state: AgentState | None = result.get("state", None)

            # Extract context information using helper method
            context, context_summary = self._extract_context_info(raw_state, result)

            if meta["is_new_thread"] and self.config.thread_name_generator_path:
                messages_str = [msg.text() for msg in messages]
                thread_name = await self._save_thread_name(
                    config, config["thread_id"], messages_str
                )
                meta["thread_name"] = thread_name

            return GraphInvokeOutputSchema(
                messages=messages,
                state=raw_state.model_dump(serialize_as_any=True) if raw_state else None,
                context=context,
                summary=context_summary,
                meta=meta,
            )

        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph execution failed: {e!s}")

    async def stream_graph(
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
    ) -> AsyncIterable[str]:
        """
        Streams the graph execution with the provided input.

        Args:
            graph_input (GraphInputSchema): The input data for graph execution.
            stream_mode (str): The stream mode ("values", "updates", "messages", etc.).

        Yields:
            str: Individual JSON chunks from graph execution with newline delimiters.

        Raises:
            HTTPException: If graph streaming fails.
        """
        try:
            logger.debug(f"Streaming graph with input: {graph_input.messages}")

            # Prepare the config
            input_data, config, meta = await self._prepare_input(graph_input)
            # add user inside config
            config["user"] = user
            config["user_id"] = user.get("user_id", "anonymous")

            # Try to save thread info in the db even for existing threads
            # this will help in updating last accessed time
            # and get is thread newly created or not, this way it's consistent
            is_new_thread = await self._save_thread(config, config["thread_id"])
            if is_new_thread and type(is_new_thread) is bool:
                meta["is_new_thread"] = True

            messages_str = []

            # Stream the graph execution
            async for chunk in self._graph.astream(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            ):
                mt = chunk.metadata or {}
                mt.update(meta)
                chunk.metadata = mt
                yield chunk.model_dump_json(serialize_as_any=True) + "\n"
                if (
                    self.config.thread_name_generator_path
                    and meta["is_new_thread"]
                    and chunk.event == StreamEvent.MESSAGE
                    and chunk.message
                    and not chunk.message.delta
                ):
                    messages_str.append(chunk.message.text())

            logger.info("Graph streaming completed successfully")

            if meta["is_new_thread"] and self.config.thread_name_generator_path:
                thread_name = await self._save_thread_name(
                    config, config["thread_id"], messages_str
                )
                meta["thread_name"] = thread_name

                yield (
                    StreamChunk(
                        event=StreamEvent.UPDATES,
                        data={"status": "completed"},
                        metadata=meta,
                    ).model_dump_json(serialize_as_any=True)
                    + "\n"
                )

        except Exception as e:
            logger.error(f"Graph streaming failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph streaming failed: {e!s}")

    async def graph_details(self) -> GraphSchema:
        try:
            logger.info("Getting graph details")
            # Fetch and return graph details
            res = self._graph.generate_graph()
            return GraphSchema(**res)
        except Exception as e:
            logger.error(f"Failed to get graph details: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get graph details: {e!s}")

    async def get_state_schema(self) -> dict:
        try:
            logger.info("Getting state schema")
            # Fetch and return state schema
            res: BaseModel = self._graph._state
            return res.model_json_schema()
        except Exception as e:
            logger.error(f"Failed to get state schema: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get state schema: {e!s}")

    def _has_empty_tool_call(self, msg: Message) -> bool:
        """Return True if any tool call on the message has empty content.

        A tool call is considered empty if its ``content`` attribute/key is ``None`` or
        an empty string. Tool calls may be dict-like or objects with a ``content`` attribute.
        """
        tool_calls = getattr(msg, "tools_calls", None)
        if not tool_calls:
            return False
        for tool_call in tool_calls:
            content = (
                tool_call.get("content")
                if isinstance(tool_call, dict)
                else getattr(tool_call, "content", None)
            )
            if content in (None, ""):
                return True
        return False

    async def fix_graph(
        self,
        thread_id: str,
        user: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fix graph state by removing messages with empty tool call content.

        This method retrieves the current state from the checkpointer, identifies messages
        with tool calls that have empty content, removes those messages, and updates the
        state.

        Args:
            thread_id (str): The thread ID to fix the graph state for
            user (dict): User information for context
            config (dict, optional): Additional configuration for the operation

        Returns:
            dict: Result dictionary containing:
                - success (bool): Whether the operation was successful
                - message (str): Status message
                - removed_count (int): Number of messages removed
                - state (dict): Updated state after fixing

        Raises:
            HTTPException: If the operation fails
        """
        try:
            logger.info(f"Starting fix graph operation for thread: {thread_id}")
            logger.debug(f"User info: {user}")

            fix_config = {"thread_id": thread_id, "user": user}
            fix_config["user_id"] = user.get("user_id", "anonymous")
            if config:
                fix_config.update(config)

            logger.debug("Fetching current state from checkpointer")
            state: AgentState | None = await self.checkpointer.aget_state(fix_config)
            if not state:
                logger.warning(f"No state found for thread: {thread_id}")
                return {
                    "success": False,
                    "message": f"No state found for thread: {thread_id}",
                    "removed_count": 0,
                    "state": None,
                }

            messages: list[Message] = list(state.context or [])
            logger.debug(f"Found {len(messages)} messages in state")
            if not messages:
                return {
                    "success": True,
                    "message": "No messages found in state",
                    "removed_count": 0,
                    "state": state.model_dump_json(serialize_as_any=True),
                }

            filtered = [m for m in messages if not self._has_empty_tool_call(m)]
            removed_count = len(messages) - len(filtered)

            if removed_count:
                state.context = filtered
                await self.checkpointer.aput_state(fix_config, state)
                message = f"Successfully removed {removed_count} message(s)"
            else:
                message = "No messages with empty tool calls found"

            return {
                "success": True,
                "message": message,
                "removed_count": removed_count,
                "state": state.model_dump_json(serialize_as_any=True),
            }
        except Exception as e:
            logger.error(f"Fix graph operation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Fix graph operation failed: {e!s}")

    async def setup(self, data: GraphSetupSchema) -> dict:
        # lets create tools
        remote_tools = defaultdict(list)
        for tool in data.tools:
            remote_tools[tool.node_name].append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )

        # Now call setup on graph
        for node_name, tool in remote_tools.items():
            self._graph.attach_remote_tools(tool, node_name)

        return {
            "status": "success",
            "details": f"Added tools to nodes: {list(remote_tools.keys())}",
        }
