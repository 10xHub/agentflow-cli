# 10xgraph-api (API server + CLI) — Engineering Guide

This file documents the **API server and CLI package** only (`10xgraph-api`). For the
core framework see `agentflow/CLAUDE.md`; for the TS client, docs, or playground see their folders;
for the monorepo overview see the workspace-root `CLAUDE.md`.

- Package name (PyPI): `10xgraph-api` (formerly `10xscale-agentflow-cli`, last release 0.6.x)
- Version: `0.7.0` (`pyproject.toml`), the first release under the 10xGraph name. `CLI_VERSION`
  and `tenxgraph_api.__version__` are single-sourced from the installed distribution metadata
  (falling back to `pyproject.toml` only for a non-installed source checkout).
- Requires: Python >= 3.12 · Status: `4 - Beta`
- Console entry points: `10xgraph = tenxgraph_api.cli.main:main`, plus the deprecated alias
  `agentflow = tenxgraph_api.cli.main:legacy_main` (prints a notice to stderr; removed in 2.0)
- Depends on the core framework: `10xgraph>=0.10.1,<2.0` (import `tenxgraph`). Must not be
  installed alongside the old `10xscale-agentflow`: both provide an `agentflow` module.

## Rename compatibility (kept until 2.0)

| Old name | New name | How the old one keeps working |
|---|---|---|
| import `agentflow_cli` | `tenxgraph_api` | `agentflow_cli/__init__.py` is a meta-path alias (same module objects, one `DeprecationWarning`) |
| command `agentflow` | `10xgraph` | second console script, `legacy_main` |
| `agentflow.json` | `10xgraph.json` | `cli/core/config.py` (`config_names`, `resolve_default_config`) and `graph_config.default_config_path()` try `10xgraph.json` first in each directory |
| `AGENTFLOW_NO_FULLSCREEN` / `_NO_SPINNER` / `_ASCII` | `TENXGRAPH_*` | `capabilities.cli_env_name()` |
| WS subprotocol `agentflow-bearer` | `10xgraph-bearer` | both accepted in `core/auth/permissions.py` |
| media URL `agentflow://media/` | `graph://media/` | core `tenxgraph.utils.media_scheme` helpers; both are ownership-checked |

Deliberately unchanged: error code `AGENTFLOW_VALIDATION_ERROR`, the `agentflow.cli/v1` JSON
output schema id, `AF-*` CLI error codes.

## What this package is

It turns a 10xGraph `CompiledGraph` into a production FastAPI service, plus a Typer CLI to
scaffold, run, build, test, and evaluate that service. You write a graph, point `10xgraph.json`
at it, and `10xgraph api` serves it over REST + WebSocket with auth, rate limiting, media
handling, checkpointer/thread management, and a memory store API.

## Package layout

Importable package: `tenxgraph_api/`. Two halves:

| Path | What lives there |
|---|---|
| `tenxgraph_api/cli/` | The Typer CLI. `main.py` (command definitions), `commands/` (one class per command: api, build, eval, init, skills, test, version), `core/` (config, output, validation), `constants.py`, `templates/` (project scaffolds: `dev/` minimal, `prod/` full) |
| `tenxgraph_api/src/app/` | The FastAPI app. `main.py` + `loader.py` (build app from `10xgraph.json`), `routers/` (graph, checkpointer, store, media, ping, ag_ui), `core/auth/`, `core/config/`, `core/middleware/` (rate_limit, security_headers, request_limits), `tasks/`, `utils/`, `worker.py` |

Public exports from the package root (`from tenxgraph_api import ...`): `BaseAuth`,
`SnowFlakeIdGenerator`, `ThreadNameGenerator`.

## CLI commands (verified against `cli/main.py`)

| Command | Purpose | Notable options |
|---|---|---|
| `10xgraph api` | Start the API server | `--config/-c` (default `10xgraph.json`), `--host/-H`, `--port/-p` (8000), `--reload/--no-reload`, `-v/-q` |
| `10xgraph play` | Start the server and open the hosted playground | same as `api` |
| `10xgraph dev` | Goal-oriented local dev server: same runner as `api`, opens the playground by default. `api`/`play` stay for compatibility | same as `api`, plus `--open/--no-open` |
| `10xgraph init` | Interactively scaffold a project (guided prompts pick dev vs production, auth, rate limit) | `--path/-p`, `--force/-f`, `--name`, `--template` (quick-start\|production), `--auth` (none\|jwt\|custom), `--rate-limit` (none\|memory\|redis), `--yes/-y`, `--non-interactive`, `--dry-run`. There is **no `--prod` flag** |
| `10xgraph build` | Generate a `Dockerfile` (and optionally `docker-compose.yml` / `k8s.yaml`) | `--output/-o`, `--force/-f`, `--python-version` (3.13), `--port`, `--docker-compose/--no-docker-compose`, `--k8s/--no-k8s`, `--service-name` |
| `10xgraph eval` | Run agent evaluations; discovers `*_eval.py`/`eval_*.py`, runs cases (optionally `--parallel`), writes HTML+JSON to `eval_reports/` | `--output/-o`, `--no-report`, `--threshold/-t`, `--open`, `--parallel/-p`, `--max-concurrency/-c` |
| `10xgraph test` | Run project tests via pytest (args after `--` forwarded verbatim) | `--coverage/-C`, `--html`, `-k`, path arg |
| `10xgraph skills` | Install the bundled 10xGraph skill (Agent Skills spec) for Codex/Claude/GitHub, or validate skills | `--agent/-a`, `--path/-p`, `--force/-f`, `--all`, `--list/-l`, `--validate PATH` |
| `10xgraph version` | Show CLI + core framework version | both resolve from installed distribution metadata |
| `10xgraph audit` | Read-only audit of the interpreter, installed CLI/core packages, evaluation-API compatibility, `10xgraph.json`, and the default port. Exits `1` on failure, `0` on warnings only, so it works as a CI gate | `-v/--verbose`, `-q/--quiet` |
| `10xgraph demo` | Preview the animation/timeline/progress themes with no side effects (`Diagnostics` help panel) | `--style` (all\|typing\|network\|init\|build\|eval; `play`/`api` alias to typing/network) |
| `10xgraph config` | Browser editor for `10xgraph.json` (`Manage` panel). Loopback-only stdlib HTTP server in `cli/config_editor/` (`schema.py` lists every key, `validation.py` reuses the `graph_config` parsers, `store.py` does conflict-checked atomic writes with a `.bak`). The page is a Preact + Tailwind app whose source lives in `config-editor-ui/`; `npm run build` there writes the committed `static/app.js` and `static/app.css`, so rebuild after editing `config-editor-ui/src` | `--config/-c`, `--port/-p` (0 = any free port), `--open/--no-open` |

Defaults (from `cli/constants.py`): `DEFAULT_HOST="127.0.0.1"`, `DEFAULT_PORT=8000`,
`DEFAULT_CONFIG_FILE="10xgraph.json"`.

Root options apply to every command and are resolved in `main.root`:
`--format` (human\|plain\|json\|jsonl), `--json`, `--color` (auto\|always\|never),
`--no-color`, `--progress` (auto\|tty\|plain\|json\|quiet),
`--animation/--no-animation`, `--fullscreen/--no-fullscreen`, `--cwd`, `-v/--verbose`
(counted), `-q/--quiet`, `--debug`, `-y/--yes`, `--non-interactive`, `-V/--version`.
`TENXGRAPH_NO_FULLSCREEN=1` (legacy `AGENTFLOW_NO_FULLSCREEN`) opts out of the
alternate-screen surface.

## `10xgraph.json` (the config contract)

Parsed by `tenxgraph_api/src/app/core/config/graph_config.py`. Supported keys:

| Key | Meaning |
|---|---|
| `agent` (required) | `"module:attribute"` resolving to a `CompiledGraph`. The loader accepts a `CompiledGraph` object, a sync/async factory returning one, or a callable. |
| `env` | Path to a `.env` file, loaded at config-load time |
| `thread_name_generator` | `"module:attr"` -> a `ThreadNameGenerator` |
| `auth` | `null`, the string `"jwt"`, or `{"method": "custom", "path": "module:attr"}` |
| `authorization` | `"module:attr"` -> an `AuthorizationBackend` (RBAC / per-tool access) |
| `checkpointer` | `"module:attr"` -> a `BaseCheckpointer` |
| `injectq` | `"module:attr"` -> an InjectQ container |
| `store` | `"module:attr"` -> a `BaseStore` |
| `redis` | Redis URL string |
| `rate_limit` | Object (see below) |
| `ag_ui` | `{"enabled": bool}`, default off. Mounts `POST /v1/ag-ui` (AG-UI protocol, for CopilotKit and other AG-UI clients). Needs the `ag-ui` extra |

`rate_limit` object: `enabled`, `requests` (default 100), `window` secs (60), `by` (`ip` |
`global`), `backend` (`memory` | `redis` | `custom`), `trusted_proxy_headers` (honour
`X-Forwarded-For` only when true), `exclude_paths`, `fail_open` (on backend error: allow vs deny),
and for redis backend a `redis` sub-object `{ "url", "prefix" }` (or shorthand URL string). For
`custom`, bind a `BaseRateLimitBackend` in InjectQ.

## Auth

- `"auth": "jwt"` requires `JWT_SECRET_KEY` and `JWT_ALGORITHM` in the environment (raises at
  load if missing). JWT logic lives in `core/auth/jwt_auth.py`.
- `"auth": {"method": "custom", "path": "module:attr"}` loads your `BaseAuth` subclass
  (`from tenxgraph_api import BaseAuth`).
- Authorization (RBAC / object-level) is separate: `core/auth/authorization.py`
  (`AuthorizationBackend` / `DefaultAuthorizationBackend` / `OwnershipAuthorizationBackend`),
  wired via the `authorization` key. That key accepts `"module:attr"` (custom), a built-in
  name (`"ownership"` = owner-only thread access; `"allow_all"`/`"default"`/`"none"`), or
  `null`. When unset it defaults **by mode**: `ownership` in production (secure by default),
  `allow_all` in development. Selection lives in `loader._resolve_authorization_backend`;
  `RequirePermission` passes `resource_id` (thread_id from path or body) to `authorize`.
- **Ownership is object-level and enforced on every thread-touching step** (invoke/stream/
  stop/fix + all checkpointer read/write/delete): a thread is accessible only to its owner;
  a foreign `invoke`/`stream` is rejected up front (403), never reaching the graph.
- **Scalable, not a DB call per request.** Ownership is immutable, so it is cached by
  `core/auth/ownership_resolver.py::ThreadOwnershipResolver`: in-process LRU (L1) + optional
  shared Redis (L2, reuses `config.redis`/`settings.REDIS_URL`). The backing lookup is
  `BaseCheckpointer.aget_thread_owner` (implemented in pg/in-memory/sqlite; base raises
  `NotImplementedError`). Cache is evicted on thread delete (`CheckpointerService.delete_thread`);
  the L2 client is closed in the lifespan shutdown.
- **Secure by construction:** `core/auth/route_guard.py::assert_all_routes_protected` runs at
  boot (`main.py` after `init_routes`) and refuses to start if any non-public route lacks a
  `RequirePermission` guard (`/ping` is the only public path).

## HTTP + WebSocket surface (all under `/v1` except ping)

- **Graph** (`tags=["Graph"]`): `POST /v1/graph/invoke`, `POST /v1/graph/stream`,
  `POST /v1/graph/stop`, `POST /v1/graph/fix`, `GET /v1/graph`,
  `WS /v1/graph/ws`.
- **Checkpointer / threads**: `GET/POST /v1/threads`, `GET/DELETE /v1/threads/{thread_id}`,
  `GET /v1/threads/{thread_id}/state`, `GET /v1/threads/{thread_id}/messages`,
  `... /messages/{message_id}`.
- **Store (memory)**: `POST /v1/store/memories`, `/v1/store/memories/list`,
  `/v1/store/memories/forget`, `/v1/store/memories/{memory_id}`, `POST /v1/store/search`.
- **Media / files** (`tags=["Files"]`): `POST /v1/files/upload`, `GET /v1/files/{file_id}`,
  `/{file_id}/info`, `/{file_id}/url`, `GET /v1/config/multimodal`.
- **AG-UI** (`tags=["AG-UI"]`, only when `ag_ui.enabled`): `POST /v1/ag-ui`. `routers/ag_ui/`:
  `converter.py` (RunAgentInput -> new user/tool messages only; the checkpoint is the record),
  `event_mapper.py` (StreamChunk -> AG-UI events), `service.py` (runs `GraphService.stream_chunks`).
  `RUN_FINISHED` carries an `outcome` only for `interrupt()` pauses (CopilotKit's pinned
  `@ag-ui/core` 0.0.59 rejects the newer `success`/`cancelled` outcome shapes). Browser tools
  from `RunAgentInput.tools` go to the graph as the server-owned `remote_tools` run-config key
  (via `GraphService.stream_chunks(..., server_config=...)`); `RunAgentInput.resume` becomes the
  graph `resume` input. `GraphInputSchema.resume` also resumes over `/v1/graph/invoke|stream`.
- **Ping**: `GET /ping`.

Routers are wired in `routers/setup_router.py` (`init_routes`). The `a2a.py` / `a2ui.py` stubs
were removed in the 0.5.0 readiness pass; they were fully commented out and never mounted.

## Settings / environment

`core/config/settings.py` is a `pydantic-settings` `Settings` (with `extra="allow"`, so unknown
env vars are tolerated). Notable vars: `APP_NAME`, `APP_VERSION`, `MODE` (`development` |
`production`), `LOG_LEVEL`, `IS_DEBUG`, `MAX_REQUEST_SIZE` (10MB default), security headers
(`SECURITY_HEADERS_ENABLED`, `HSTS_*`, `FRAME_OPTIONS`, `CSP_POLICY`, ...), `ORIGINS` (CORS,
default `*` with a wildcard warning), `ALLOWED_HOST`, `ROOT_PATH`/`DOCS_PATH`/`REDOCS_PATH`,
`REDIS_URL`, `SENTRY_DSN`, `SNOWFLAKE_*` (epoch/node/worker/bit layout), `JWT_SECRET_KEY`/
`JWT_ALGORITHM`, `OTEL_ENABLED`/`OTEL_SERVICE_NAME`/`OTEL_EXPORTER_OTLP_ENDPOINT`/`OTEL_LEVEL`.
In production: set `MODE=production`, `IS_DEBUG=false`, a non-`*` `ORIGINS`, and a strong
`JWT_SECRET_KEY`.

## Optional extras (`pyproject.toml`)

`sentry`, `firebase`, `snowflakekit`, `redis`, `jwt`, `ag-ui` (AG-UI endpoint), `media` (document text extraction via
`textxtract`), `gcloud` (Cloud Logging), `otel` (includes FastAPI instrumentation + OTLP exporter).

## Development workflow

```bash
# from this folder (10xgraph-api/); a .venv is present
.venv/bin/python -m pytest                 # tests in tests/
10xgraph init                             # scaffold (interactive)
10xgraph api --reload                     # dev server on 127.0.0.1:8000
10xgraph play                             # server + hosted playground
10xgraph build --docker-compose           # Dockerfile + compose
ruff check . && ruff format .
```

- Tests in `tests/`; `pytest` config and ruff/bandit are in `pyproject.toml`. Templates under
  `cli/templates/{dev,prod}` are excluded from lint/type/bandit (they are emitted code, not lib).
- The `prod` template is the reference for a real project: it scaffolds `graph/` (agent, state,
  tools, validators, thread_name_generator), `auth/`, `evals/`, and `tests/`.

## Known doc drift (do not trust without checking)

- **Version is now single-sourced.** `CLI_VERSION` (and `tenxgraph_api.__version__`, which aliases
  it) resolve from installed distribution metadata. `10xgraph version` prints the CLI version and
  the installed core `10xgraph` version; the old `pyproject.toml` path read - which
  printed `unknown` from a wheel - is gone.
- **There is no `agentflow doctor`.** The environment check shipped as `10xgraph audit`; earlier
  README/CHANGELOG copy called it `doctor`. Anything still saying `doctor` is stale.
- **README links to `./docs/`** (`configuration.md`, `authentication.md`, `deployment.md`,
  `id-generation.md`, `thread-name-generator.md`) but there is no `docs/` directory in this
  package — every one of those links is broken.
- **a2a / a2ui routers no longer exist.** Don't document a2a HTTP endpoints as live; restore the
  files from git history if that surface is actually built.
- **`pyproject.toml` URLs** point at `10xgraph.com` and `github.com/10xGraph/10xgraph-api`,
  but the git remote is still `Iamsdt/pyagenity-api.git` and needs to be repointed before
  release (checklist 1.5).
- The workspace-root `CLAUDE.md` lists only `init/api/play/build` and an older `10xgraph.json`
  shape; the real CLI has `eval/test/skills/version` too and the config supports `rate_limit`,
  `thread_name_generator`, and `authorization`.
