"""Translate 10xGraph ``StreamChunk`` output into AG-UI protocol events.

One mapper handles one run. It tracks which text, reasoning and step blocks are open so the
event stream always follows the AG-UI ordering rules: ``RUN_STARTED`` first, every ``START``
before its ``CONTENT`` and ``END``, everything closed before the single terminal
``RUN_FINISHED`` or ``RUN_ERROR``.

10xGraph emits a model turn either as a series of delta messages followed by a final message
with a new id (streaming providers), or as one final message (plain function nodes). Text that
was already streamed is not sent again from the final message. Tool calls are only complete in
the final message, so ``TOOL_CALL_START/ARGS/END`` are sent from there in one go.

A graph paused by ``interrupt()`` ends the run with ``RUN_FINISHED`` and an ``interrupt``
outcome, which clients answer with ``RunAgentInput.resume``. Otherwise ``RUN_FINISHED`` carries no
``outcome``: CopilotKit's pinned ``@ag-ui/core`` (0.0.59 in CopilotKit 1.75) rejects the
``success`` outcome's newer fields and the ``cancelled`` outcome.
"""

from __future__ import annotations

import json
from typing import Any

import ag_ui.core as agui
from ag_ui.core import (
    BaseEvent,
    Interrupt,
    ReasoningEndEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    ReasoningStartEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunFinishedInterruptOutcome,
    RunStartedEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from tenxgraph.core.state import AgentState, Message, StreamChunk, StreamEvent, ToolCallBlock
from tenxgraph.core.state.message_block import RemoteToolCallBlock
from tenxgraph.utils.constants import END, START


# Graph bookkeeping nodes, not steps a user cares about.
_HIDDEN_NODES = frozenset({START, END})

# AgentState fields that are not application state: the conversation travels as messages,
# and execution metadata is internal.
_INTERNAL_STATE_FIELDS = frozenset({"context", "context_summary", "execution_meta"})


def app_state(state: AgentState) -> dict[str, Any]:
    """The application fields of ``state``, as JSON, for a ``STATE_SNAPSHOT``."""
    return state.model_dump(mode="json", exclude=set(_INTERNAL_STATE_FIELDS))


class AgUiEventMapper:
    """Stateful translator for one AG-UI run.

    Call :meth:`start` once, :meth:`map` for every chunk, then :meth:`finish`. After a
    ``RUN_ERROR`` (from :meth:`fail` or an error chunk) every later call returns nothing.
    """

    def __init__(
        self,
        thread_id: str,
        run_id: str,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self.thread_id = thread_id
        self.run_id = run_id
        self.finished = False
        self._text_id: str | None = None
        self._reasoning_id: str | None = None
        # The text message the current model turn produced, as parent for its tool calls.
        self._turn_text_id: str | None = None
        self._turn_streamed = False
        self._open_steps: list[str] = []
        self._tool_calls: set[str] = set()
        self._tool_results: set[str] = set()
        self._last_state = initial_state or None
        self._interrupt: dict[str, Any] | None = None

    def start(self) -> list[BaseEvent]:
        extra: dict[str, Any] = {}
        protocol_version = getattr(agui, "PROTOCOL_VERSION", None)
        if protocol_version and "protocol_version" in RunStartedEvent.model_fields:
            extra["protocol_version"] = protocol_version
        return [RunStartedEvent(thread_id=self.thread_id, run_id=self.run_id, **extra)]

    def map(self, chunk: StreamChunk) -> list[BaseEvent]:
        if self.finished:
            return []
        if chunk.event == StreamEvent.MESSAGE and chunk.message is not None:
            return self._on_message(chunk.message)
        if chunk.event == StreamEvent.UPDATES:
            return self._on_update(chunk.data or {})
        if chunk.event == StreamEvent.STATE and chunk.state is not None:
            return self._on_state(chunk.state)
        if chunk.event == StreamEvent.ERROR:
            return self._on_error(chunk.data or {})
        return []

    def map_state(self, state: AgentState) -> list[BaseEvent]:
        """A ``STATE_SNAPSHOT`` for ``state``, when it differs from what the client has."""
        if self.finished:
            return []
        return self._on_state(state)

    def report_interrupt(self, interrupt: dict[str, Any]) -> None:
        """End the run as paused at ``interrupt`` (a ``tenxgraph`` ``Interrupt`` as JSON)."""
        self._interrupt = interrupt

    def finish(self) -> list[BaseEvent]:
        if self.finished:
            return []
        events = self._close_all()
        self.finished = True
        extra: dict[str, Any] = {}
        if self._interrupt is not None:
            extra["outcome"] = RunFinishedInterruptOutcome(
                interrupts=[_agui_interrupt(self._interrupt)]
            )
        events.append(RunFinishedEvent(thread_id=self.thread_id, run_id=self.run_id, **extra))
        return events

    def fail(self, message: str, code: str | None = None) -> list[BaseEvent]:
        if self.finished:
            return []
        events = self._close_all()
        self.finished = True
        events.append(RunErrorEvent(message=message, code=code))
        return events

    # ------------------------------------------------------------------ messages

    def _on_message(self, message: Message) -> list[BaseEvent]:
        if message.role == "assistant":
            return self._on_delta(message) if message.delta else self._on_final(message)
        if message.role == "tool":
            return self._on_tool_result(message)
        return []  # the user's own message echoed back

    def _on_delta(self, message: Message) -> list[BaseEvent]:
        message_id = str(message.message_id)
        events: list[BaseEvent] = []
        for block in message.content:
            if block.type == "reasoning" and block.summary:
                events += self._reasoning(message_id, block.summary)
            elif block.type == "text" and block.text:
                events += self._text(message_id, block.text)
        return events + self._on_tool_calls(message)

    def _on_final(self, message: Message) -> list[BaseEvent]:
        message_id = str(message.message_id)
        events: list[BaseEvent] = []
        if not self._turn_streamed:
            reasoning = "\n\n".join(
                b.summary for b in message.content if b.type == "reasoning" and b.summary
            )
            text = "".join(b.text for b in message.content if b.type == "text" and b.text)
            if reasoning:
                events += self._reasoning(message_id, reasoning)
            if text:
                events += self._text(message_id, text)
        events += self._close_reasoning() + self._close_text()
        events += self._on_tool_calls(message, fallback_parent=message_id)
        self._turn_text_id = None
        self._turn_streamed = False
        return events

    def _on_tool_calls(
        self, message: Message, fallback_parent: str | None = None
    ) -> list[BaseEvent]:
        calls = [c for c in _tool_calls(message) if c[0] not in self._tool_calls]
        if not calls:
            return []
        events = self._close_reasoning() + self._close_text()
        parent = self._turn_text_id
        if parent is None:
            # Announce the parent message so the client has something to attach the call to.
            parent = fallback_parent or str(message.message_id)
            events += [
                TextMessageStartEvent(message_id=parent, role="assistant"),
                TextMessageEndEvent(message_id=parent),
            ]
            self._turn_text_id = parent
        for call_id, name, arguments in calls:
            self._tool_calls.add(call_id)
            events += [
                ToolCallStartEvent(
                    tool_call_id=call_id, tool_call_name=name, parent_message_id=parent
                ),
                ToolCallArgsEvent(tool_call_id=call_id, delta=arguments),
                ToolCallEndEvent(tool_call_id=call_id),
            ]
        return events

    def _on_tool_result(self, message: Message) -> list[BaseEvent]:
        events: list[BaseEvent] = []
        for block in message.content:
            if block.type != "tool_result" or block.call_id in self._tool_results:
                continue
            message_id = str(message.message_id)
            if events:
                message_id = f"{message_id}-{block.call_id}"
            events.append(self._tool_result(message_id, block.call_id, _stringify(block.output)))
        return events

    def _tool_result(self, message_id: str, call_id: str, content: str) -> ToolCallResultEvent:
        self._tool_results.add(call_id)
        return ToolCallResultEvent(
            message_id=message_id, tool_call_id=call_id, content=content, role="tool"
        )

    # --------------------------------------------------------- text and reasoning

    def _text(self, message_id: str, delta: str) -> list[BaseEvent]:
        events = self._close_reasoning()
        if self._text_id != message_id:
            events += self._close_text()
            events.append(TextMessageStartEvent(message_id=message_id, role="assistant"))
            self._text_id = message_id
            self._turn_text_id = message_id
        self._turn_streamed = True
        events.append(TextMessageContentEvent(message_id=message_id, delta=delta))
        return events

    def _reasoning(self, message_id: str, delta: str) -> list[BaseEvent]:
        reasoning_id = f"{message_id}-reasoning"
        events = self._close_text()
        if self._reasoning_id != reasoning_id:
            events += self._close_reasoning()
            events += [
                ReasoningStartEvent(message_id=reasoning_id),
                ReasoningMessageStartEvent(message_id=reasoning_id),
            ]
            self._reasoning_id = reasoning_id
        self._turn_streamed = True
        events.append(ReasoningMessageContentEvent(message_id=reasoning_id, delta=delta))
        return events

    def _close_text(self) -> list[BaseEvent]:
        if self._text_id is None:
            return []
        events: list[BaseEvent] = [TextMessageEndEvent(message_id=self._text_id)]
        self._text_id = None
        return events

    def _close_reasoning(self) -> list[BaseEvent]:
        if self._reasoning_id is None:
            return []
        reasoning_id = self._reasoning_id
        self._reasoning_id = None
        return [
            ReasoningMessageEndEvent(message_id=reasoning_id),
            ReasoningEndEvent(message_id=reasoning_id),
        ]

    def _close_all(self) -> list[BaseEvent]:
        events = self._close_reasoning() + self._close_text()
        while self._open_steps:
            events.append(StepFinishedEvent(step_name=self._open_steps.pop()))
        return events

    # ------------------------------------------------------ updates, state, errors

    def _on_update(self, data: dict[str, Any]) -> list[BaseEvent]:
        if data.get("status") == "interrupted" and isinstance(data.get("interrupt"), dict):
            self.report_interrupt(data["interrupt"])
            return []
        node = data.get("node")
        if not isinstance(node, str) or node in _HIDDEN_NODES:
            return []
        status = data.get("status")
        if status == "invoking_node" and node not in self._open_steps:
            self._open_steps.append(node)
            return [StepStartedEvent(step_name=node)]
        if status == "node_invoked" and node in self._open_steps:
            self._open_steps.remove(node)
            return [StepFinishedEvent(step_name=node)]
        return []

    def _on_state(self, state: AgentState) -> list[BaseEvent]:
        snapshot = app_state(state)
        if not snapshot or snapshot == self._last_state:
            return []
        self._last_state = snapshot
        return [StateSnapshotEvent(snapshot=snapshot)]

    def _on_error(self, data: dict[str, Any]) -> list[BaseEvent]:
        if data.get("status") == "tool_failed":
            # A failed tool is a result the model reacts to, not the end of the run.
            call_id = data.get("tool_call_id")
            if not call_id or call_id in self._tool_results:
                return []
            # ``error`` holds the tool's own message; ``reason`` is a generic summary.
            reason = data.get("error") or data.get("reason") or "Tool failed"
            return [self._tool_result(f"{call_id}-error", str(call_id), f"Error: {reason}")]
        return self.fail(str(data.get("reason") or "Graph execution failed"), "GRAPH_ERROR")


def _tool_calls(message: Message) -> list[tuple[str, str, str]]:
    """``(id, name, JSON arguments)`` for each tool call in ``message``, without duplicates.

    A call can appear both in ``tools_calls`` (OpenAI shape, drives execution) and as a
    content block (drives rendering).
    """
    calls: dict[str, tuple[str, str, str]] = {}
    for call in message.tools_calls or []:
        if not isinstance(call, dict) or not call.get("id"):
            continue
        function = call.get("function") or {}
        name = function.get("name") or call.get("name") or ""
        arguments = function.get("arguments", call.get("args"))
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments or {})
        calls.setdefault(str(call["id"]), (str(call["id"]), str(name), arguments or "{}"))
    for block in message.content:
        if isinstance(block, ToolCallBlock | RemoteToolCallBlock) and block.id:
            calls.setdefault(block.id, (block.id, block.name, json.dumps(block.args or {})))
    return list(calls.values())


def _agui_interrupt(interrupt: dict[str, Any]) -> Interrupt:
    """An AG-UI ``Interrupt`` for a ``tenxgraph`` interrupt; its payload goes in metadata."""
    return Interrupt(
        id=str(interrupt.get("id")),
        reason=str(interrupt.get("reason") or "input_required"),
        message=interrupt.get("message"),
        tool_call_id=interrupt.get("tool_call_id"),
        response_schema=interrupt.get("response_schema"),
        metadata={"value": interrupt.get("value"), "node": interrupt.get("node")},
    )


def _stringify(output: Any) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if hasattr(output, "model_dump"):
        output = output.model_dump(mode="json")
    return json.dumps(output, default=str)
