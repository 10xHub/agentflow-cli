# StreamEmitter

Emit live progress, errors, and status updates from tools during streaming execution.

## Overview

`StreamEmitter` allows tools to send **live progress updates** back to the caller during `app.stream(...)` / `app.astream(...)` execution. Tools can report intermediate steps, retries, and errors in real-time without using an external publisher.

## Key Points

- **Streaming only**: Automatically injected during `app.stream()` / `app.astream()`, not during `invoke()` / `ainvoke()`
- **Optional parameter**: Declare as `emit: StreamEmitter | None = None` in tool functions
- **Thread-safe**: Works with both sync and async tools
- **Built-in**: Uses the same streaming pipeline; no external publisher required

## Common Methods

### `progress(message: str, data: dict | None = None)`

Emit a progress update showing intermediate steps or status changes.

```python
if emit:
    emit.progress("Fetching data...", data={"attempt": 1, "max_attempts": 3})
```

### `error(message: str, data: dict | None = None)`

Emit an error update (informational; doesn't interrupt execution).

```python
if emit:
    emit.error("API timeout, using cache", data={"retry_count": 3})
```

### `message(message: str, data: dict | None = None)`

Emit a plain informational message.

```python
if emit:
    emit.message("Processing complete", data={"items_processed": 1000})
```

### `update(data: dict)`

Emit a generic data update without a message.

```python
if emit:
    emit.update({
        "status": "batch_progress",
        "processed": 50,
        "total": 100,
        "percentage": 50.0,
    })
```

## Usage Pattern

```python
from agentflow.core.state.stream_emitter import StreamEmitter

def my_tool(
    param: str,
    emit: StreamEmitter | None = None,
) -> str:
    """Tool that reports progress during streaming."""
    if emit:
        emit.progress("Starting work...")
    
    # ... do work ...
    
    if emit:
        emit.progress("Finalizing...", data={"step": 2})
    
    return "result"
```

## When to Use

✅ **Use for:**
- Long-running operations (API calls, file processing)
- Retries with multiple attempts
- Multi-step processes
- Batch processing with progress tracking

❌ **Don't use for:**
- Fast operations (<100ms)
- Non-streaming paths (emit will be None anyway)
- Critical control flow (always return a result regardless)

## Behavior

| Execution Mode | Emit Parameter | Output |
|---|---|---|
| `app.stream()` | `StreamEmitter` | Progress updates in stream |
| `app.astream()` | `StreamEmitter` | Progress updates in stream |
| `app.invoke()` | `None` | No progress updates |
| `app.ainvoke()` | `None` | No progress updates |

## Stream Output

Emitted chunks appear in the stream output with structure:

```python
{
    "event": "message" | "error" | "update",
    "data": {
        "status": "tool_progress" | "tool_failed" | "tool_message" | ...,
        "tool_name": "my_tool",
        "tool_call_id": "call_abc123",
        "node": "TOOL",
        "message": "...",
        "thread_id": "...",
        "run_id": "...",
        # ... plus any extra data passed
    },
}
```

## Performance Tips

- Emit at meaningful intervals, not every iteration
- For batch work: emit every N items, not on every item
- Avoid thousands of updates per second

```python
# ❌ Too frequent
for item in items:
    if emit:
        emit.progress(f"Processing {item}")

# ✅ Batched
for i, item in enumerate(items):
    if (i + 1) % 100 == 0 and emit:
        emit.progress(f"Processed {i + 1} of {len(items)}")
```

## See Also

- [Tools](agents-and-tools.md) — Defining and registering tools
- [Streaming](streaming.md) — Overview of streaming chunks
- [Dependency Injection](dependency-injection.md) — How parameters like `emit` are injected
