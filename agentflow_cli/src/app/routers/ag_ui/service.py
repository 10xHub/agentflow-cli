"""Run the graph for one AG-UI request and stream the result as AG-UI events."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from agentflow.utils import ResponseGranularity

from agentflow_cli.src.app.core import logger
from agentflow_cli.src.app.core.auth.request_config import tool_result_ids
from agentflow_cli.src.app.routers.graph.schemas.graph_schemas import GraphInputSchema
from agentflow_cli.src.app.routers.graph.services.graph_service import GraphService

from .converter import select_new_messages, to_agentflow_messages
from .event_mapper import AgUiEventMapper


# Graph config key holding the AG-UI request extras (frontend context, tools, forwarded props),
# so graph nodes and tools can read them from ``config["ag_ui"]``.
AG_UI_CONFIG_KEY = "ag_ui"

# Client state keys that would overwrite the conversation or execution metadata.
_RESERVED_STATE_KEYS = frozenset({"context", "context_summary", "execution_meta"})


async def stream_ag_ui(
    service: GraphService,
    run_input: RunAgentInput,
    user: dict[str, Any],
    encoder: EventEncoder,
) -> AsyncIterator[str]:
    """Stream one AG-UI run as encoded events.

    The thread's checkpoint is the record of the conversation: only client messages it has not
    seen are sent to the graph. A run with nothing new (a client syncing state) still gets a
    complete ``RUN_STARTED`` / ``RUN_FINISHED`` pair, with the thread's state.
    """
    initial_state = _client_state(run_input.state)
    mapper = AgUiEventMapper(run_input.thread_id, run_input.run_id, initial_state=initial_state)
    for event in mapper.start():
        yield encoder.encode(event)

    try:
        checkpoint_state = await _checkpoint_state(service, run_input.thread_id, user)
        context = list(getattr(checkpoint_state, "context", None) or [])
        new_messages = select_new_messages(
            run_input.messages,
            known_ids={str(m.message_id) for m in context},
            answered_call_ids=set(tool_result_ids(context)),
        )
        messages = to_agentflow_messages(new_messages)
        _warn_unknown_tools(service, run_input)

        if not messages:
            if checkpoint_state is not None:
                for event in mapper.map_state(checkpoint_state):
                    yield encoder.encode(event)
        else:
            graph_input = GraphInputSchema(
                messages=messages,
                initial_state=initial_state,
                config={
                    "thread_id": run_input.thread_id,
                    "run_id": run_input.run_id,
                    AG_UI_CONFIG_KEY: {
                        "context": [c.model_dump(mode="json") for c in run_input.context or []],
                        "tools": [t.model_dump(mode="json") for t in run_input.tools or []],
                        "forwarded_props": run_input.forwarded_props,
                    },
                },
                response_granularity=ResponseGranularity.FULL,
            )
            async for chunk in service.stream_chunks(graph_input, user):
                for event in mapper.map(chunk):
                    yield encoder.encode(event)
    except ValueError as exc:
        logger.warning("AG-UI run rejected: %s", exc)
        for event in mapper.fail(str(exc), "INVALID_INPUT"):
            yield encoder.encode(event)
    except Exception as exc:
        # The response has already started, so the failure has to travel in the stream.
        logger.error("AG-UI run failed: %s", exc)
        for event in mapper.fail("AG-UI run failed", "AG_UI_ERROR"):
            yield encoder.encode(event)

    for event in mapper.finish():
        yield encoder.encode(event)


def _client_state(state: Any) -> dict[str, Any] | None:
    if not isinstance(state, dict):
        return None
    cleaned = {k: v for k, v in state.items() if k not in _RESERVED_STATE_KEYS}
    return cleaned or None


async def _checkpoint_state(service: GraphService, thread_id: str, user: dict[str, Any]) -> Any:
    if service.checkpointer is None:
        return None
    config = {
        "thread_id": thread_id,
        "user": user,
        "user_id": user.get("user_id", "anonymous"),
    }
    return await service.checkpointer.aget_state(config)


def _warn_unknown_tools(service: GraphService, run_input: RunAgentInput) -> None:
    """Frontend tools reach the model only when agentflow.json declares them.

    AG-UI clients send their tools with every run, but the graph's client-side tools are the
    ``remote_tools`` configured at startup. Name the ones the model cannot see so the gap is
    easy to find.
    """
    sent = {tool.name for tool in run_input.tools or []}
    unknown = sorted(sent - service._remote_tool_names())
    if unknown:
        logger.warning(
            "AG-UI client tools not declared in agentflow.json remote_tools, "
            "so the model cannot call them: %s",
            ", ".join(unknown),
        )
