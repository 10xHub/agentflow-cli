# 10xgraph-api 0.7.0

## Agentflow is now 10xGraph

This is the first release of the API server and CLI as **`10xgraph-api`**. It replaces
`10xscale-agentflow-cli`, whose last release was 0.6.x. The server, the CLI, the HTTP API,
the license and the maintainers are the same. Only the names change.

| | Before | Now |
|---|---|---|
| PyPI package | `10xscale-agentflow-cli` | `10xgraph-api` |
| Python import | `agentflow_cli` | `tenxgraph_api` |
| Command | `agentflow` | `10xgraph` |
| Config file | `agentflow.json` | `10xgraph.json` |
| Core framework | `10xscale-agentflow` (import `agentflow`) | `10xgraph` (import `tenxgraph`) |
| Website | agentflow.10xscale.ai | [10xgraph.com](https://10xgraph.com) |
| GitHub | github.com/10xHub | [github.com/10xGraph](https://github.com/10xGraph) |

## Upgrading

```bash
pip uninstall 10xscale-agentflow-cli 10xscale-agentflow
pip install 10xgraph-api
```

Uninstall the old core too: `10xscale-agentflow` and `10xgraph` both ship an `agentflow`
module and must not be installed side by side.

Your project keeps working without edits:

- `agentflow.json` is still read when there is no `10xgraph.json` next to it. Rename it
  when convenient; the keys are the same.
- The `agentflow` command still runs, with a one-line deprecation notice.
- `from agentflow_cli import BaseAuth` still works, with a `DeprecationWarning`.
- `AGENTFLOW_NO_FULLSCREEN`, `AGENTFLOW_NO_SPINNER` and `AGENTFLOW_ASCII` are still read
  when the `TENXGRAPH_` variables are unset.
- Released TypeScript clients keep working: the server still accepts the
  `agentflow-bearer` WebSocket subprotocol and `agentflow://media/` references.

These aliases are removed in 2.0.

## Check before you deploy

- **Logger names** are now `tenxgraph_api.*`. Update logging config that targets
  `agentflow-cli.*`, `agentflow_api.*` or `agentflowcli`.
- **Redis rate-limit keys** default to the `10xgraph:rate-limit` prefix, so counters restart
  once. A `prefix` set in your config is kept.
- **Skills:** `10xgraph skills` installs the skill as `10xgraph`. Delete old `agentflow`
  skill folders once the new one is in place.

See `CHANGELOG.md` for the full list.
