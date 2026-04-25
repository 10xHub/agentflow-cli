# Dependency Injection

Use this when wiring services into nodes/tools, configuring API dependencies, or removing hidden globals.

## Automatic Injection

Agentflow injects these parameters by name/type conventions when they appear in node or tool signatures:

- `state`: current `AgentState` or subclass.
- `config`: execution config such as `thread_id`, `user_id`, and `run_id`.
- `tool_call_id`: current tool call ID, tools only.

Injected parameters are hidden from the model-facing tool schema.

## Service Injection

Use `injectq` for application services:

```python
from injectq import Inject, InjectQ

container = InjectQ.get_instance()
container.bind_instance(MyService, service)

def tool(query: str, service: MyService = Inject[MyService]) -> str:
    """Search with MyService."""
    return service.search(query)
```

You can bind singleton instances, string keys, or factories. Pass a container to `StateGraph(container=container)` when using a non-default container.

## API Configuration

In `agentflow.json`, use import paths to wire dependencies into the server runtime:

```json
{
  "agent": "graph.react:app",
  "checkpointer": "graph.dependencies:checkpointer",
  "store": "graph.dependencies:store",
  "injectq": "graph.dependencies:container"
}
```

The API loader imports these and binds them for graph execution.

## Rules

- Prefer `InjectQ` over module-level globals for databases, stores, callbacks, and custom services.
- Keep user-provided tool arguments model-visible; keep runtime context injected.
- Configure shared services at graph/server boundaries, not deep inside individual tools.

## Source Map

- DI docs source: `agentflow-docs/docs/concepts/dependency-injection.md`
- API loader: `agentflow-api/agentflow_cli/src/app/loader.py`
- Graph config: `agentflow-api/agentflow_cli/src/app/core/config/graph_config.py`
- Tool/node call helpers: `agentflow/agentflow/utils/callable_utils.py`
