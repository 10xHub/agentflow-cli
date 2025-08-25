from collections.abc import AsyncIterator
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from injector import inject, singleton
from pyagenity.graph import CompiledGraph
from pyagenity.state import AgentState
from pyagenity.utils import Message
from snowflakekit import SnowflakeGenerator

from src.app.core import logger
from src.app.core.config.settings import get_settings
from src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphStreamChunkSchema,
    MessageSchema,
)

from .thread_service import ThreadService


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
        generator: SnowflakeGenerator,
        thread_service: ThreadService,
    ):
        """
        Initializes the GraphService with a CompiledGraph instance.

        Args:
            graph (CompiledGraph): An instance of CompiledGraph for
                                   graph execution operations.
        """
        self.settings = get_settings()
        self._graph = graph
        self._generator = generator
        self._thread_service = thread_service

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

            role = msg.role if msg.role in allowed_roles else "user"
            # Cast role to the expected Literal type for type checking
            # System role are not allowed for safety reasons
            # Fixme: Fix message id
            converted_msg = Message.from_text(
                role=role,  # type: ignore
                data=msg.content,
                message_id=msg.message_id,  # type: ignore
            )
            converted_messages.append(converted_msg)

        return converted_messages

    def _serialize_chunk(self, chunk):
        """
        Serialize any object to a JSON-compatible format.

        Args:
            chunk: The chunk object to serialize

        Returns:
            JSON-serializable representation of the chunk
        """
        # If it's already a basic JSON type, return as-is
        if chunk is None or isinstance(chunk, str | int | float | bool):
            return chunk

        # Handle collections recursively
        if isinstance(chunk, dict):
            return {key: self._serialize_chunk(value) for key, value in chunk.items()}
        if isinstance(chunk, list | tuple):
            return [self._serialize_chunk(item) for item in chunk]

        # Try various serialization methods and fallbacks
        serialization_attempts = [
            lambda: chunk.model_dump() if hasattr(chunk, "model_dump") else None,
            lambda: chunk.to_dict() if hasattr(chunk, "to_dict") else None,
            lambda: chunk.dict() if hasattr(chunk, "dict") else None,
            lambda: self._serialize_chunk(chunk.__dict__) if hasattr(chunk, "__dict__") else None,
            lambda: str(chunk),  # Final fallback
        ]

        for attempt in serialization_attempts:
            try:
                result = attempt()
                if result is not None:
                    return result
            except Exception as e:
                logger.debug(f"Serialization attempt failed: {e}")
                continue

        return str(chunk)  # Should never reach here, but just in case

    async def _prepare_input(
        self,
        graph_input: GraphInputSchema,
    ):
        is_new_thread = False
        config = graph_input.config or {}
        if "thread_id" in config:
            thread_id = config["thread_id"]
        else:
            thread_id = await self._generator.generate()
            is_new_thread = True

        # update thread id
        config["thread_id"] = thread_id

        # check recursion limit set or not
        config["recursion_limit"] = graph_input.recursion_limit or 25

        # Prepare the input for the graph
        input_data = {
            "messages": self._convert_messages(
                graph_input.messages,
            ),
            "state": graph_input.initial_state or {},
        }

        return (
            input_data,
            config,
            {
                "is_new_thread": is_new_thread,
                "thread_id": thread_id,
            },
        )

    async def invoke_graph(
        self,
        graph_input: GraphInputSchema,
        user: dict[str, Any],
        background_tasks: BackgroundTasks,
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

            # Execute the graph
            result = await self._graph.ainvoke(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            )

            logger.info("Graph execution completed successfully")

            # Extract messages from result and convert back to dictionaries
            messages: list[Message] = result.get("messages", [])
            state: AgentState | None = result.get("state", None)
            context: list[Message] | None = result.get("context", None)
            context_summary: str | None = result.get("context_summary", None)

            # if not found read from state
            if not context_summary and state:
                context_summary = state.context_summary

            if not context and state:
                context = state.context

            # Generate background thread name
            # background_tasks.add_task(self._generate_background_thread_name, thread_id)

            if self.settings.GENERATE_THREAD_NAME:
                background_tasks.add_task(
                    self._thread_service.save_thread_name,
                    config,
                    config["thread_id"],
                    messages,
                )

            return GraphInvokeOutputSchema(
                messages=messages,
                state=state,
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
        background_tasks: BackgroundTasks,
    ) -> AsyncIterator[GraphStreamChunkSchema]:
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

            # Stream the graph execution
            async for chunk in await self._graph.astream(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            ):
                # Convert any objects in the chunk to JSON-serializable format
                processed_chunk = self._serialize_chunk(chunk)

                yield GraphStreamChunkSchema(
                    data=(
                        processed_chunk
                        if isinstance(processed_chunk, dict)
                        else {"chunk": processed_chunk}
                    ),
                    metadata=meta,
                )

            logger.info("Graph streaming completed successfully")
            # background_tasks.add_task(self._generate_background_thread_name, thread_id)
            # save threads
            # if self.settings.GENERATE_THREAD_NAME:
            #     await self._thread_service.save_thread_name(config, config["thread_id"], messages)

        except Exception as e:
            logger.error(f"Graph streaming failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph streaming failed: {e!s}")
