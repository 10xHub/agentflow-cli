# API Configuration

Use this when changing `agentflow.json`, dependency loading, app startup, or graph import behavior.

## `agentflow.json`

Minimal:

```json
{
  "agent": "graph.react:app"
}
```

Common full shape:

```json
{
  "agent": "graph.react:app",
  "checkpointer": "graph.dependencies:my_checkpointer",
  "store": "graph.dependencies:my_store",
  "injectq": "graph.dependencies:container",
  "thread_name_generator": "graph.thread_name_generator:MyNameGenerator",
  "authorization": "graph.auth:my_authorization_backend",
  "env": ".env",
  "auth": "jwt"
}
```

## Fields

- `agent`: required import path to a compiled graph variable, in `module.path:attribute` format.
- `checkpointer`: optional import path to a `BaseCheckpointer` instance.
- `store`: optional import path to a `BaseStore` instance; required for store endpoints.
- `injectq`: optional import path to an `InjectQ` container.
- `thread_name_generator`: optional import path to a thread-name generator class/instance.
- `authorization`: optional import path to an authorization backend.
- `env`: optional `.env` path loaded before graph import.
- `auth`: `null`, `"jwt"`, or `{"method": "custom", "path": "module:backend"}`.

## Loading Order

1. Read `agentflow.json`.
2. Load `.env` when configured.
3. Import the compiled graph from `agent`.
4. Import and bind `checkpointer`, `store`, `injectq`, `thread_name_generator`, and `authorization` when configured.
5. Configure auth.
6. Start FastAPI routes and services.

## Rules

- Keep graph modules importable from the project root.
- Keep `agent` pointing to a compiled graph object, not an uncompiled `StateGraph`.
- Keep dependency modules side-effect light.
- Load secrets through `.env` or process environment, not committed config.
- Validate import paths early and surface clear CLI/API errors.

## Source Map

- Graph config: `agentflow-api/agentflow_cli/src/app/core/config/graph_config.py`
- Loader: `agentflow-api/agentflow_cli/src/app/loader.py`
- App startup: `agentflow-api/agentflow_cli/src/app/main.py`
- Main docs: `agentflow-docs/docs/reference/api-cli/configuration.md`
- How-to: `agentflow-docs/docs/how-to/api-cli/configure-agentflow-json.md`
