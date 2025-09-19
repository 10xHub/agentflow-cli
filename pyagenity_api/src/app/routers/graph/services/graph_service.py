from collections.abc import AsyncIterable
from typing import Any
from uuid import uuid4
from fastapi import BackgroundTasks, HTTPException
from injectq import InjectQ, inject, singleton
from pyagenity.checkpointer import BaseCheckpointer
from pyagenity.graph import CompiledGraph
from pyagenity.utils import ContentType, Message
from pydantic import BaseModel
from starlette.responses import Content

from pyagenity_api.src.app.core import logger
from pyagenity_api.src.app.core.config.graph_config import GraphConfig
from pyagenity_api.src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphSchema,
    MessageSchema,
)
from pyagenity_api.src.app.routers.graph.services.dummy_name_generator import (
    generate_dummy_thread_name,
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
        thread_service: ThreadService,
        checkpointer: BaseCheckpointer,
        config: GraphConfig,
    ):
        """
        Initializes the GraphService with a CompiledGraph instance.

        Args:
            graph (CompiledGraph): An instance of CompiledGraph for
                                   graph execution operations.
        """
        self._graph = graph
        self._thread_service = thread_service
        self.config = config
        self.checkpointer = checkpointer

    async def _save_thread(self, config: dict[str, Any], thread_id: int):
        """
        Save the generated thread name to the database.
        """
        return await self.checkpointer.aput_thread(
            config,
            {
                "thread_id": thread_id,
                "thread_name": generate_dummy_thread_name(),
            },
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
            thread_id = await InjectQ.get_instance().atry_get("generated_id") or str(uuid4())
            is_new_thread = True

        # update thread id
        config["thread_id"] = str(thread_id)

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
                "thread_id": str(thread_id),
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
            raw_state = result.get("state", None)
            context: list[Message] | None = result.get("context", None)
            context_summary: str | None = result.get("context_summary", None)

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

            # Generate background thread name
            # background_tasks.add_task(self._generate_background_thread_name, thread_id)

            if meta["is_new_thread"] and self.config.generate_thread_name:
                model_name = self.config.thread_model_name
                if not model_name:
                    logger.warning(
                        "Thread model name is not configured, cannot generate thread name",
                    )
                else:
                    background_tasks.add_task(
                        self._thread_service.generate_thread_name_invoke,
                        config,
                        config["thread_id"],
                        messages,
                    )

            # state can be instance of pydentic or dict
            state_dict = raw_state.model_dump() if raw_state is not None else raw_state  # type: ignore

            return GraphInvokeOutputSchema(
                messages=messages,
                state=state_dict,
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

            accumulated_messages: list[dict[str, Any]] = []

            # Stream the graph execution
            async for chunk in self._graph.astream(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            ):
                mt = chunk.metadata or {}
                mt.update(meta)
                chunk.metadata = mt
                if (
                    (
                        meta["is_new_thread"]
                        and chunk.content_type is not None
                        and ContentType.MESSAGE in chunk.content_type
                    )
                    and chunk.data is not None
                    and "message" in chunk.data
                ):
                    accumulated_messages.append(chunk.data.get("message", {}))

                yield chunk.model_dump_json()

            logger.info("Graph streaming completed successfully")

            if meta["is_new_thread"] and self.config.generate_thread_name:
                model_name = self.config.thread_model_name
                if not model_name:
                    logger.warning(
                        "Thread model name is not configured, cannot generate thread name",
                    )
                else:
                    background_tasks.add_task(
                        self._thread_service.generate_thread_name_stream,
                        config,
                        config["thread_id"],
                        accumulated_messages,
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
