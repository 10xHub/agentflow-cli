# StateGraph and Nodes

Use this when adding workflows, nodes, edges, interrupts, graph compilation, or execution behavior.

## Core Model

`StateGraph` is the workflow engine. A graph describes directed node execution over an `AgentState` subclass. The compiled graph handles state loading, node execution, routing, checkpointing, streaming, interrupts, recursion limits, and shutdown.

## Creating Graphs

- `StateGraph()` uses `AgentState`.
- `StateGraph(MyState)` or `StateGraph(MyState())` uses a custom Pydantic state subclass.
- Constructor-level dependencies include optional context manager, publisher, ID generator, and `InjectQ` container.

## Nodes

A node can be:

- A callable receiving state and returning a `Message`, `ToolResult`, or state dict.
- An `Agent`.
- A `ToolNode`.
- Any compatible sync or async function.

Use `graph.add_node("NAME", node)` for explicit naming. Use `graph.add_node(function)` only when the function name is the right node name. Use `graph.override_node("NAME", replacement)` in tests or controlled overrides.

## Edges

- `add_edge("A", "B")`: static transition.
- `set_entry_point("A")`: starts graph at a node.
- `add_conditional_edges("A", route, path_map)`: route by state-derived string keys.
- Use `END` for termination.
- Use `Command` for runtime jumps only when static or conditional edges are not enough; see `callbacks-and-command.md`.

## Compilation

`graph.compile(...)` accepts:

- `checkpointer`: state persistence; defaults to in-memory where implementation supplies it.
- `store`: long-term memory store.
- `media_store`: multimodal file store.
- `interrupt_before` / `interrupt_after`: pause points.
- `callback_manager`: observability hooks.
- `shutdown_timeout`: graceful close timeout.

Compilation should fail fast when the entry point is missing or interrupt nodes do not exist.

For callbacks, validators, and tracing hooks, read `callbacks-and-command.md`.

## Execution

- `app.invoke(input, config, response_granularity)` runs synchronously and returns a dict.
- `app.ainvoke(...)` is the async equivalent.
- `app.stream(...)` yields sync `StreamChunk` values.
- `app.astream(...)` yields async `StreamChunk` values.
- `config.thread_id` enables checkpointed continuity.
- `config.recursion_limit` caps node execution count.

## Interrupts

Compile with `interrupt_before=["NODE"]` or `interrupt_after=["NODE"]`. Resume by invoking again with the same `thread_id`.

## Source Map

- StateGraph: `agentflow/agentflow/core/graph/state_graph.py`
- Compiled graph: `agentflow/agentflow/core/graph/compiled_graph.py`
- Graph errors: `agentflow/agentflow/core/exceptions`
- Constants: `agentflow/agentflow/utils/constants.py`
