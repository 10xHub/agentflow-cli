# Context, ID Generation, and Background Tasks

Use this when changing context trimming, generated IDs, background work, or graceful shutdown.

## Context Managers

`MessageContextManager` controls what conversation history is sent to the model without deleting stored state.

Use it for:

- Token budget control.
- Preserving important system/tool messages.
- Summarizing or trimming old context.
- Custom context policies per graph.

Pass a context manager to `StateGraph(context_manager=...)`. Custom managers should subclass `BaseContextManager` and implement the required transform behavior.

## ID Generators

Import ID generators from `agentflow.utils`.

Built-ins:

- `DefaultIDGenerator`
- `UUIDGenerator`
- `BigIntIDGenerator`
- `TimestampIDGenerator`
- `IntIDGenerator`
- `HexIDGenerator`
- `ShortIDGenerator`
- `AsyncIDGenerator`

Related types:

- `BaseIDGenerator`
- `IDType`

Pass an ID generator to `StateGraph(id_generator=...)`. Generated IDs can be accessed through runtime config/container patterns where supported.

## Background Tasks

`BackgroundTaskManager` manages async background work such as non-blocking memory writes.

Important methods:

- `create_task`
- `get_task_count`
- `get_task_info`
- `wait_for_all`
- `cancel_all`
- `shutdown`

Use `TaskMetadata` for task tracking.

## Graceful Shutdown

Utilities include:

- `GracefulShutdownManager`
- `DelayedKeyboardInterrupt`
- `delayed_keyboard_interrupt`
- `shutdown_with_timeout`
- `setup_exception_handler`

Use these when a process needs to stop streams, wait for background tasks, and close publishers or storage clients cleanly.

## Rules

- Context managers change model input, not persisted checkpointer history.
- ID generator changes can affect API/client assumptions; verify serialized ID types.
- Always wait for or cancel background tasks during shutdown.
- Keep background task payloads bounded and avoid capturing large graph state unless needed.

## Source Map

- Context managers: `agentflow/agentflow/core/state/message_context_manager.py`
- ID generators: `agentflow/agentflow/utils/id_generator.py`
- Background tasks: `agentflow/agentflow/utils/background_task_manager.py`
- Shutdown utilities: `agentflow/agentflow/utils/shutdown.py`
- Main docs: `agentflow-docs/docs/reference/python/context-manager.md`
- Main docs: `agentflow-docs/docs/reference/python/id-generator.md`
- Main docs: `agentflow-docs/docs/reference/python/background-tasks.md`
