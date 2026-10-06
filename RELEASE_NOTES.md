# 10xscale-agentflow-cli 0.6.0

## This is the final release of `10xscale-agentflow-cli`

Agentflow is now **10xGraph**. The project continues under a new name because
"Agentflow" is shared by several unrelated projects, which made it hard to find.
Nothing about the server, the CLI, the license or the maintainers changes.

No further versions of `10xscale-agentflow-cli` will be published to PyPI. Existing
installs keep working; pin `10xscale-agentflow-cli==0.6.0` if you need to stay on it.

| | Before | After |
|---|---|---|
| Core framework | `10xscale-agentflow` | `10xgraph` (import `tenxgraph`) |
| API server + CLI | `10xscale-agentflow-cli` | `10xgraph-api` |
| Website | agentflow.10xscale.ai | [10xgraph.com](https://10xgraph.com) |
| GitHub | github.com/10xHub | [github.com/10xGraph](https://github.com/10xGraph) |

This release depends on `10xscale-agentflow>=0.10.0`, the final release of the core under
the old name. Do not install `10xgraph` in the same environment: both provide the
`agentflow` module and must not be installed side by side. Your `agentflow.json` and graph
code carry over. To migrate:

```bash
pip uninstall 10xscale-agentflow-cli 10xscale-agentflow
pip install 10xgraph-api
```

## Highlights

- **AG-UI endpoint (`POST /v1/ag-ui`).** Serve the graph to AG-UI clients such as
  CopilotKit. Off by default: set `"ag_ui": {"enabled": true}` and install the `ag-ui`
  extra. Streams text, reasoning, tool calls, node steps, state snapshots and `interrupt()`
  pauses; browser tools sent by the client are offered to the model for that run.
- **Resume interrupted runs.** `/v1/graph/invoke` and `/v1/graph/stream` accept `resume` to
  continue a thread paused by `interrupt()`.
- **`agentflow config` is a browser editor for `agentflow.json`**, with validation before
  save and a `.bak` of the previous file.
- **`remote_tools` in `agentflow.json`** declares client-executed tools, attached at startup.
- **`agentflow skills --validate PATH`** checks skills against the Agent Skills
  specification (agentskills.io). The bundled skill now conforms to it.
- **Hardening.** Server-owned config keys (`authz`, `user`, `user_id`, `remote_tools`,
  `_*`) are stripped from client requests; client messages can no longer carry tool calls;
  document extraction is bounded; WebSocket connections have finite default limits,
  including a per-user cap; `rate_limit.trusted_proxies` controls when `X-Forwarded-For` is
  trusted.

## Breaking changes

- **`POST /v1/graph/setup` is removed.** Declare client-executed tools under `remote_tools`
  in `agentflow.json`.
- **`agentflow config list|get|set|unset|path|validate` are removed**, and stored `output.*`
  preferences are no longer read. Pass `--format`, `--color` and `--progress` instead.
- **WebSocket limits default to 1000 connections per process and 10 per user** when not
  configured (previously unlimited). Set `websocket.max_connections` or
  `websocket.max_connections_per_user` to `0` or `null` for unlimited.
- **Requires `10xscale-agentflow>=0.10.0`.**

## Upgrading

```bash
pip install --upgrade "10xscale-agentflow-cli==0.6.0"
```

See `CHANGELOG.md` for the full list.
