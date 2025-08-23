from collections.abc import AsyncIterator

from fastapi import BackgroundTasks, HTTPException
from injector import inject, singleton
from pyagenity.graph import CompiledGraph
from pyagenity.state import AgentState
from pyagenity.utils import Message
from snowflakekit import SnowflakeGenerator

from src.app.core import logger
from src.app.routers.graph.schemas.graph_schemas import (
    GraphInputSchema,
    GraphInvokeOutputSchema,
    GraphStreamChunkSchema,
    MessageSchema,
)


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
    ):
        """
        Initializes the GraphService with a CompiledGraph instance.

        Args:
            graph (CompiledGraph): An instance of CompiledGraph for
                                   graph execution operations.
        """
        self._graph = graph
        self._generator = generator

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

    async def _prepare_input(
        self,
        graph_input: GraphInputSchema,
    ):
        config = graph_input.config or {}
        thread_id = graph_input.thread_id or await self._generator.generate()
        is_new_thread = bool(not graph_input.thread_id)
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

            # Execute the graph
            result = await self._graph.ainvoke(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            )

            logger.info("Graph execution completed successfully")

            # Extract messages from result and convert back to dictionaries
            messages: list[Message] = result.get("messages", [])
            final_response = []
            final_response = [
                msg.to_dict(
                    include_raw=graph_input.include_raw,
                )
                for msg in messages
            ]

            state: AgentState | None = result.get("state", None)
            context_message = []
            if state and state.context:
                context_message = [
                    msg.to_dict(
                        include_raw=graph_input.include_raw,
                    )
                    for msg in state.context
                ]

            # Generate background thread name
            # background_tasks.add_task(self._generate_background_thread_name, thread_id)

            return GraphInvokeOutputSchema(
                messages=final_response,
                state=state.to_dict(include_internal=graph_input.include_raw) if state else None,
                context=context_message,
                summary=state.context_summary if state else None,
                meta=meta,
            )

        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph execution failed: {e!s}")

    async def stream_graph(
        self,
        graph_input: GraphInputSchema,
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

            # Stream the graph execution
            async for chunk in self._graph.astream(
                input_data,
                config=config,
                response_granularity=graph_input.response_granularity,
            ):
                # Convert any Message objects in the chunk to dictionaries
                processed_chunk = chunk
                if isinstance(chunk, dict):
                    converted_chunk = {}
                    for key, value in chunk.items():
                        if hasattr(value, "to_dict"):
                            converted_chunk[key] = value.to_dict()
                        elif isinstance(value, list):
                            converted_chunk[key] = [
                                item.to_dict() if hasattr(item, "to_dict") else item
                                for item in value
                            ]
                        else:
                            converted_chunk[key] = value
                    processed_chunk = converted_chunk

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

        except Exception as e:
            logger.error(f"Graph streaming failed: {e}")
            raise HTTPException(status_code=500, detail=f"Graph streaming failed: {e!s}")
