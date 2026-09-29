# StateGraph and Nodes

Use this when adding workflows, nodes, edges, interrupts, graph compilation, or execution behavior.

---

## Core model

`StateGraph` is the workflow engine. A graph describes a directed set of nodes and edges executed over an `AgentState` subclass. The compiled graph manages state loading, routing, checkpointing, streaming, interrupts, recursion limits, and shutdown automatically.

---

## Creating a StateGraph

### Minimal

```python
from agentflow.core.graph import StateGraph

graph = StateGraph()   # defaults to AgentState
```

### Custom state class

```python
from agentflow.core.state import AgentState

class OrderState(AgentState):
    order_id: str = ""
    total: float = 0.0

graph = StateGraph(OrderState)   # pass class or instance — both work
```

### Full constructor

```python
StateGraph(
    state: StateT | None = None,
    context_manager: BaseContextManager | None = None,
    publisher: BasePublisher | None = None,
    id_generator: BaseIDGenerator = DefaultIDGenerator(),
    container: InjectQ | None = None,
)
```

| Parameter | Description |
|---|---|
| `state` | State class or instance. Defaults to `AgentState()` |
| `context_manager` | Optional cross-node state transformer (trim context, summarise, etc.) |
| `publisher` | Optional publisher for emitting lifecycle events (Kafka, Redis Pub/Sub, RabbitMQ) |
| `id_generator` | Strategy for generating message and run IDs |
| `container` | `InjectQ` container for DI. Defaults to the global singleton |

---

## Adding nodes

A node is any callable that receives `AgentState` (or subclass) and returns a `Message`, `ToolResult`, or state `dict`.

```python
graph.add_node("MAIN", agent)          # explicit name
graph.add_node("TOOL", tool_node)
graph.add_node(process)                # auto-name: "process"
graph.override_node("MAIN", mock)      # replace existing node — useful in tests
```

---

## Edges

```python
graph.add_edge("TOOL", "MAIN")             # static: always TOOL → MAIN
graph.set_entry_point("MAIN")              # shorthand for add_edge(START, "MAIN")
```

### Conditional edges

The routing function receives `AgentState` and returns a string key. `path_map` maps that key to a node name:

```python
from agentflow.utils.constants import END

def route(state: AgentState) -> str:
    last = state.context[-1]
    if hasattr(last, "tools_calls") and last.tools_calls and last.role == "assistant":
        return "TOOL"
    if last.role == "tool":
        return "MAIN"
    return END

graph.add_conditional_edges("MAIN", route, {"TOOL": "TOOL", END: END})
# If path_map is omitted, the function must return the destination node name directly.
```

Use `Command(goto=...)` for runtime jumps only when static or conditional edges are insufficient. See `callbacks-and-command.md`.

---

## Compiling

```python
from agentflow.utils import CallbackManager

app = graph.compile(
    checkpointer=checkpointer,       # BaseCheckpointer | None
    store=store,                     # BaseStore | None
    media_store=media_store,         # BaseMediaStore | None
    interrupt_before=["VALIDATOR"],  # pause before these node names
    interrupt_after=["TOOL"],        # pause after these node names
    callback_manager=CallbackManager(),
    shutdown_timeout=30.0,
)
```

| Parameter | Type | Description |
|---|---|---|
| `checkpointer` | `BaseCheckpointer \| None` | State persistence. Defaults to `InMemoryCheckpointer` if not provided |
| `store` | `BaseStore \| None` | Long-term cross-thread memory store |
| `media_store` | `BaseMediaStore \| None` | Media file storage for multimodal content |
| `interrupt_before` | `list[str] \| None` | Pause before these node names |
| `interrupt_after` | `list[str] \| None` | Pause after these node names |
| `callback_manager` | `CallbackManager` | Hooks for observability and lifecycle events |
| `shutdown_timeout` | `float` | Seconds to wait for graceful shutdown (default `30.0`) |

`compile()` raises `GraphError` if no entry point is set or if interrupt nodes do not exist.

---

## Invoking

```python
from agentflow.core.state import Message
from agentflow.utils import ResponseGranularity

result = app.invoke(
    {"messages": [Message.text_message("Hello!")]},
    config={"thread_id": "t1", "recursion_limit": 25},
    response_granularity=ResponseGranularity.LOW,
)
messages = result["messages"]
```

`ainvoke()` is the async equivalent. Returns the full state dict.

### Lifecycle / async context manager

`CompiledGraph` supports `async with`; `aclose()` runs on exit even if the body raises, and is
idempotent (a second call returns `{"status": "already_closed"}`).

```python
async with await build_and_compile_graph() as graph:
    await graph.ainvoke(input_data)
# aclose() runs automatically here
```

---

## Streaming

```python
from agentflow.core.state.stream_chunks import StreamEvent

for chunk in app.stream(
    {"messages": [Message.text_message("Hello!")]},
    config={"thread_id": "t2"},
):
    if chunk.event == StreamEvent.MESSAGE and chunk.message:
        print(chunk.message.text())
```

`astream()` is the async equivalent. See `streaming.md` for full details on `StreamChunk` fields and `StreamEvent` values.

### Realtime (audio) graphs

A graph rooted at a `LiveAgent` is driven by `arealtime(input_queue, config=None, state=None)` (async
generator of `RealtimeEvent`s) or the sync `realtime(...)` wrapper, not `invoke` / `stream`. The
forcing rule is mutual: a graph with a `LiveAgent` must use `arealtime()` (`invoke` / `stream`
raise), and `arealtime()` requires exactly one `LiveAgent` (ordinary graphs raise). See
`realtime.md`.

---

## Config keys

Passed in the `config` dict to `invoke` / `stream`:

| Key | Type | Description |
|---|---|---|
| `thread_id` | `str` | Conversation thread identifier. Required for checkpointing |
| `user_id` | `str` | Optional user identifier; injected into tool `config` param |
| `run_id` | `str` | Optional run identifier; auto-generated if omitted |
| `recursion_limit` | `int` | Max node executions before stopping (default `25`) |

---

## Interrupts

Compile with `interrupt_before` or `interrupt_after`. When execution reaches an interrupt node, the graph pauses and persists state. Resume by calling `invoke` again with the same `thread_id` and an empty input:

```python
app = graph.compile(checkpointer=checkpointer, interrupt_before=["VALIDATOR"])

# First call — pauses before VALIDATOR
app.invoke({"messages": [Message.text_message("Start")]}, config={"thread_id": "t3"})

# Resume after review
app.invoke({}, config={"thread_id": "t3"})
```

---

## Execution lifecycle

```
app.invoke → Load or create AgentState (from checkpointer if thread_id exists)
           → Run entry node
           → Evaluate conditional or static edge
           → Run next node
           → Check for interrupt → pause and save state (if configured)
           → Repeat until END
           → Save final state → Return result dict
```

---

## Source map

- StateGraph: https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/core/graph/state_graph.py
- CompiledGraph: https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/core/graph/compiled_graph.py
- Constants (END, START): https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/utils/constants.py
- How-to (build a graph): https://agentflow.10xscale.ai/how-to/python/build-a-graph
