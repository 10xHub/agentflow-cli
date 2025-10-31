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
from starlette.responses import Content

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    MessageSchema,
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

    def _convert_messages(self, messages: list[MessageSchema]) -> list[Message]:
        """
        Convert dictionary messages to PyAgenity Message objects.

        Args:
            messages: List of dictionary messages

        Returns:
            List of PyAgenity Message objects
        """
        converted_messages = []
        allowed_roles = {"user", "assistant", "tool"}
        for msg in messages:
            if msg.role == "system":
                raise Exception("System role is not allowed for safety reasons")

            if msg.role not in allowed_roles:
                logger.warning(f"Invalid role '{msg.role}' in message, defaulting to 'user'")

            # Cast role to the expected Literal type for type checking
            # System role are not allowed for safety reasons
            # Fixme: Fix message id
            converted_msg = Message.text_message(
                content=msg.content,
                message_id=msg.message_id,  # type: ignore
            )
            converted_messages.append(converted_msg)

        return converted_messages

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
            "messages": self._convert_messages(
                graph_input.messages,
            ),
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

            # if its a new thread then save the thread into db
            await self._save_thread(config, config["thread_id"])

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
                state=raw_state.model_dump() if raw_state else None,
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
    ) -> AsyncIterable[Content]:
        """
        Streams the graph execution with the provided input.

        Args:
            graph_input (GraphInputSchema): The input data for graph execution.
            stream_mode (str): The stream mode ("values", "updates", "messages", etc.).

        Yields:
            GraphStreamChunkSchema: Individual chunks from graph execution.

        Raises:
            HTTPException: If graph streaming fails.
        """
        try:
            logger.debug(f"Streaming graph with input: {graph_input.messages}")

            # Prepare the config
            input_data, config, meta = await self._prepare_input(graph_input)
            # add user inside config
            config["user"] = user
            await self._save_thread(config, config["thread_id"])

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
                yield chunk.model_dump_json()
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
                messages_str = [msg.text() for msg in messages_str]
                thread_name = await self._save_thread_name(
                    config, config["thread_id"], messages_str
                )
                meta["thread_name"] = thread_name

                yield StreamChunk(
                    event=StreamEvent.UPDATES,
                    data={"status": "completed"},
                    metadata=meta,
                ).model_dump_json()

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
