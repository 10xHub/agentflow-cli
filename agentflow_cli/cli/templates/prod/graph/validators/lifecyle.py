"""Lifecycle hooks for the weather agent graph."""

import logging
from typing import Any

from agentflow.core.state.message import Message
from agentflow.utils.callbacks import GraphLifecycleContext, GraphLifecycleHook

from graph.state import WeatherState


logger = logging.getLogger(__name__)


class AgentLifecycleHook(GraphLifecycleHook[WeatherState]):
    async def on_graph_start(
        self,
        context: GraphLifecycleContext,
        state: WeatherState,
    ) -> WeatherState | None:
        """Hydrate ``WeatherState`` from the org config attached by AgentAuth."""
        return state

    async def on_graph_end(
        self,
        context: GraphLifecycleContext,
        final_state: WeatherState,
        messages: list[Message],
        total_steps: int,
    ) -> WeatherState | None:
        """Called after successful graph completion, before final state sync.

        Return a modified WeatherState to persist, or None to keep the current state.
        """
        return None

    async def on_graph_error(
        self,
        context: GraphLifecycleContext,
        error: Exception,
        partial_state: WeatherState,
        messages: list[Message],
        step: int,
        node_name: str,
    ) -> tuple[WeatherState, str] | None:
        """Called when an unhandled error escapes the execution loop.

        Return (modified_state, error_message) to change the persisted error snapshot,
        or None to keep the current error state. The exception is always re-raised.
        """
        return None

    async def on_interrupt(
        self,
        context: GraphLifecycleContext,
        interrupted_node: str,
        interrupt_type: str,
        state: WeatherState,
    ) -> WeatherState | None:
        """Called when execution pauses at an interrupt point.

        Return a modified WeatherState to persist at interrupt, or None to keep the current state.
        In-place mutation of the passed state is also supported.
        """
        return None

    async def on_resume(
        self,
        context: GraphLifecycleContext,
        resumed_node: str,
        state: WeatherState,
        resume_data: dict[str, Any],
    ) -> WeatherState | None:
        """Called when a previously interrupted execution is about to resume.

        Called before clear_interrupt(). Return a modified WeatherState to continue with,
        or None to use the loaded state unchanged.
        """
        return None

    async def on_checkpoint(
        self,
        context: GraphLifecycleContext,
        state: WeatherState,
        messages: list[Message],
        is_context_trimmed: bool,
    ) -> tuple[WeatherState, list[Message]] | WeatherState | None:
        """Called before every durable checkpoint write.

        Return (state, messages) to modify both, WeatherState to modify state only,
        or None to persist without modification.
        """
        return None

    async def on_state_update(
        self,
        context: GraphLifecycleContext,
        node_name: str,
        old_state: WeatherState,
        new_state: WeatherState,
        step: int,
    ) -> WeatherState | None:
        """Called after each node's result is merged into state.

        Return a modified WeatherState to replace new_state, or None to use new_state unchanged.
        """
        return None
