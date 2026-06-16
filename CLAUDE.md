# agentflow-api (API server + CLI) — Engineering Guide

This file documents the **API server and CLI package** only (`10xscale-agentflow-cli`). For the
core framework see `agentflow/CLAUDE.md`; for the TS client, docs, or playground see their folders;
for the monorepo overview see the workspace-root `CLAUDE.md`.

- Package name (PyPI): `10xscale-agentflow-cli`
- Version: `0.3.2.9` (`pyproject.toml`). `CLI_VERSION` and `agentflow_cli.__version__` are
  single-sourced from the installed distribution metadata (falling back to `pyproject.toml`), so
  `agentflow version` reports `0.3.2.9` consistently. The previous `1.0.0` hardcode is gone.
- Requires: Python >= 3.12 · Status: `4 - Beta`
- Console entry point: `agentflow = agentflow_cli.cli.main:main`
- Depends on the core framework: `10xscale-agentflow>=0.7.0`.

## What this package is

It turns an Agentflow `CompiledGraph` into a production FastAPI service, plus a Typer CLI to
scaffold, run, build, test, and evaluate that service. You write a graph, point `agentflow.json`
at it, and `agentflow api` serves it over REST + WebSocket with auth, rate limiting, media
handling, checkpointer/thread management, and a memory store API.

## Package layout

Importable package: `agentflow_cli/`. Two halves:

| Path | What lives there |
|---|---|
| `agentflow_cli/cli/` | The Typer CLI. `main.py` (command definitions), `commands/` (one class per command: api, build, eval, init, skills, test, version), `core/` (config, output, validation), `constants.py`, `templates/` (project scaffolds: `dev/` minimal, `prod/` full) |
| `agentflow_cli/src/app/` | The FastAPI app. `main.py` + `loader.py` (build app from `agentflow.json`), `routers/` (graph, checkpointer, store, media, ping; a2a/a2ui present but not mounted), `core/auth/`, `core/config/`, `core/middleware/` (rate_limit, security_headers, request_limits), `tasks/`, `utils/`, `worker.py` |

Public exports from the package root (`from agentflow_cli import ...`): `BaseAuth`,
`SnowFlakeIdGenerator`, `ThreadNameGenerator`.

## CLI commands (verified against `cli/main.py`)

| Command | Purpose | Notable options |
|---|---|---|
| `agentflow api` | Start the API server | `--config/-c` (default `agentflow.json`), `--host/-H`, `--port/-p` (8000), `--reload/--no-reload`, `-v/-q` |
| `agentflow play` | Start the server and open the hosted playground | same as `api` |
| `agentflow init` | Interactively scaffold a project (questionary prompts pick dev vs production, auth, rate limit) | `--path/-p`, `--force/-f`. There is **no `--prod` flag**; setup type is chosen interactively |
| `agentflow build` | Generate a `Dockerfile` (and optionally `docker-compose.yml`) | `--output/-o`, `--python-version` (3.13), `--port`, `--docker-compose/--no-docker-compose`, `--service-name` |
| `agentflow eval` | Run agent evaluations; discovers `*_eval.py`/`eval_*.py`, runs cases (optionally `--parallel`), writes HTML+JSON to `eval_reports/` | `--output/-o`, `--no-report`, `--threshold/-t`, `--open`, `--parallel/-p`, `--max-concurrency/-c` |
| `agentflow test` | Run project tests via pytest (args after `--` forwarded verbatim) | `--coverage/-C`, `--html`, `-k`, path arg |
| `agentflow skills` | Install bundled Agentflow skills for Codex/Claude/GitHub | `--agent/-a`, `--path/-p`, `--force/-f`, `--all`, `--list/-l` |
| `agentflow version` | Show CLI + package version | reads `CLI_VERSION` constant + package version from `pyproject.toml` |

Defaults (from `cli/constants.py`): `DEFAULT_HOST="127.0.0.1"`, `DEFAULT_PORT=8000`,
`DEFAULT_CONFIG_FILE="agentflow.json"`.

## `agentflow.json` (the config contract)

Parsed by `agentflow_cli/src/app/core/config/graph_config.py`. Supported keys:

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

`rate_limit` object: `enabled`, `requests` (default 100), `window` secs (60), `by` (`ip` |
`global`), `backend` (`memory` | `redis` | `custom`), `trusted_proxy_headers` (honour
`X-Forwarded-For` only when true), `exclude_paths`, `fail_open` (on backend error: allow vs deny),
and for redis backend a `redis` sub-object `{ "url", "prefix" }` (or shorthand URL string). For
`custom`, bind a `BaseRateLimitBackend` in InjectQ.

## Auth

- `"auth": "jwt"` requires `JWT_SECRET_KEY` and `JWT_ALGORITHM` in the environment (raises at
  load if missing). JWT logic lives in `core/auth/jwt_auth.py`.
- `"auth": {"method": "custom", "path": "module:attr"}` loads your `BaseAuth` subclass
  (`from agentflow_cli import BaseAuth`).
- Authorization (RBAC, per-tool) is separate: `core/auth/authorization.py`
  (`AuthorizationBackend` / `DefaultAuthorizationBackend`), wired via the `authorization` key.

## HTTP + WebSocket surface (all under `/v1` except ping)

- **Graph** (`tags=["Graph"]`): `POST /v1/graph/invoke`, `POST /v1/graph/stream`,
  `POST /v1/graph/stop`, `POST /v1/graph/setup`, `POST /v1/graph/fix`, `GET /v1/graph`,
  `WS /v1/graph/ws`.
- **Checkpointer / threads**: `GET/POST /v1/threads`, `GET/DELETE /v1/threads/{thread_id}`,
  `GET /v1/threads/{thread_id}/state`, `GET /v1/threads/{thread_id}/messages`,
  `... /messages/{message_id}`.
- **Store (memory)**: `POST /v1/store/memories`, `/v1/store/memories/list`,
  `/v1/store/memories/forget`, `/v1/store/memories/{memory_id}`, `POST /v1/store/search`.
- **Media / files** (`tags=["Files"]`): `POST /v1/files/upload`, `GET /v1/files/{file_id}`,
  `/{file_id}/info`, `/{file_id}/url`, `GET /v1/config/multimodal`.
- **Ping**: `GET /ping`.

Routers are wired in `routers/setup_router.py` (`init_routes`). `a2a.py` and `a2ui.py` exist but
are **not** mounted there yet.

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

`sentry`, `firebase`, `snowflakekit`, `redis`, `jwt`, `media` (document text extraction via
`textxtract`), `gcloud` (Cloud Logging), `otel` (includes FastAPI instrumentation + OTLP exporter).

## Development workflow

```bash
# from this folder (agentflow-api/); a .venv is present
.venv/bin/python -m pytest                 # tests in tests/
agentflow init                             # scaffold (interactive)
agentflow api --reload                     # dev server on 127.0.0.1:8000
agentflow play                             # server + hosted playground
agentflow build --docker-compose           # Dockerfile + compose
ruff check . && ruff format .
```

- Tests in `tests/`; `pytest` config and ruff/bandit are in `pyproject.toml`. Templates under
  `cli/templates/{dev,prod}` are excluded from lint/type/bandit (they are emitted code, not lib).
- The `prod` template is the reference for a real project: it scaffolds `graph/` (agent, state,
  tools, validators, thread_name_generator), `auth/`, `evals/`, and `tests/`.

## Known doc drift (do not trust without checking)

- **Version is now single-sourced.** `CLI_VERSION` (and `agentflow_cli.__version__`, which aliases
  it) resolve from installed distribution metadata, falling back to `pyproject.toml`. `agentflow
  version` reports `0.3.2.9` for both the CLI and package lines. (The old hardcoded `1.0.0` drift is
  resolved.)
- **README shows `agentflow init --prod`** — that flag does not exist. `init` is interactive and
  only accepts `--path` / `--force`.
- **`api`/`play` help text claims default host `0.0.0.0`** but `DEFAULT_HOST` is `127.0.0.1`.
- **"Pyagenity" branding leftovers.** The CLI app help, `agentflow_cli.__init__` docstring, the
  `version` banner, and several router docstrings still say "Pyagenity" (the framework's former
  name). Cosmetic but pervasive; rename to Agentflow when touching those files.
- **a2a / a2ui routers are not mounted.** Don't document a2a HTTP endpoints as live until
  `setup_router.init_routes` includes them.
- **`pyproject.toml` URLs** point at `github.com/10xHub/agentflow-cli` and
  `agentflow-cli.readthedocs.io`; confirm these are canonical vs the core's `agentflow.10xscale.ai`.
- The workspace-root `CLAUDE.md` lists only `init/api/play/build` and an older `agentflow.json`
  shape; the real CLI has `eval/test/skills/version` too and the config supports `rate_limit`,
  `thread_name_generator`, and `authorization`.
