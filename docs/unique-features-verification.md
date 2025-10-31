# Unique features verification

This document verifies each “Unique Features to highlight” claim from `TODOD.txt` against the current codebase and tests, adds additional highlight-worthy features, and lists concrete follow-ups to make partially true claims fully accurate.

## Overview

- Scope: `agentflow_cli` package and its FastAPI app, CLI, and tests in this repository.
- Method: traced code paths, searched for wiring, and validated behavior with existing tests.

## Claims from TODOD.txt and status

### 3) Single command to run with API (FastAPI), async-first, Uvicorn, logger, health checks, Swagger/Redoc ready, Prometheus, env-driven

Status: Verified

Evidence:
- Single-command run (development): `agentflow_cli/cli/main.py` (Typer app) provides `agentflow api`, implemented in `agentflow_cli/cli/commands/api.py` using Uvicorn to serve `agentflow_cli.src.app.main:app`.
- Health check: `GET /ping` in `agentflow_cli/src/app/routers/ping/router.py`.
- Logging: consolidated Uvicorn/Gunicorn/FastAPI logging in `agentflow_cli/src/app/core/config/setup_logs.py::init_logger()`.
- Middleware and best practices: CORS, Trusted Hosts, GZip, and Request ID headers in `agentflow_cli/src/app/core/config/setup_middleware.py`.
- Swagger/Redoc “ready”: `agentflow_cli/src/app/main.py` wires `docs_url`/`redoc_url` from env, but defaults disable them (empty -> None). Set `DOCS_PATH`/`REDOCS_PATH` to enable.
- Prometheus: `/metrics`


### 5) Single command to generate docker file, deploy anywhere

Status: Partial

Evidence:
- `agentflow build` generates a production-ready Dockerfile (and optional docker-compose.yml):
  - CLI: `agentflow_cli/cli/main.py`
  - Implementation: `agentflow_cli/cli/commands/build.py`
  - Template: `agentflow_cli/cli/templates/defaults.py::generate_dockerfile_content`
  - Tests: `tests/cli/test_cli_commands_ops.py` validate generated Dockerfile and compose toggle.
- Image build step is manual (`docker build ...`). There is no built-in flag to run the build.

Recommended follow-ups:
- Optionally add a `--build` flag to run `docker build` after generating files (kept off by default).
- Keep “deploy anywhere” claim; no vendor lock-in is consistent with generated artifacts.

### 7) Easy auth integration; JWT by default; custom providers by class path

Status: Verified

Evidence:
- JWT verification param via env (`JWT_SECRET_KEY`, `JWT_ALGORITHM`) and decoding paths:
  - `agentflow_cli/src/app/core/auth/jwt_auth.py`
  - `agentflow_cli/src/app/core/config/graph_config.py::auth_config()`
- Custom provider by class path via `agentflow.json`:
  - `graph_config.auth_config()` supports `{"method":"custom","path": ...}`
- Endpoints depend on `verify_current_user`:
  - Graph/Store/Checkpointer routers include `Depends(verify_current_user)`.

### 8) Control over generated ID (smaller IDs)

Status: Verified

Evidence:
- Optional Snowflake-based ID generator with env-tunable config:
  - `agentflow_cli/src/app/utils/snowflake_id_generator.py` (uses `snowflakekit` extra)
  - Defaults in `agentflow_cli/src/app/core/config/settings.py`
- Exported from package `__init__.py`.

Note:
- Feature exists and is ready; usage sites depend on downstream integration needs.

### 9) State, message, tool calls are Pydantic models, JSON serializable

Status: Verified (for API layer)

Evidence:
- Extensive Pydantic schemas for requests/responses:
  - Graph: `agentflow_cli/src/app/routers/graph/schemas/graph_schemas.py`
  - Checkpointer: `.../checkpointer/schemas/checkpointer_schemas.py`
  - Store: `.../store/schemas/store_schemas.py`
  - Swagger helpers and output envelopes: `agentflow_cli/src/app/utils/swagger_helper.py`, `.../utils/schemas/output_schemas.py`
- “Tool calls” specifics are in the upstream `agentflow` library; here they are surfaced through typed API contracts.

### 10) Sentry integration ready; provide DSN to send exceptions

Status: Partial

Evidence:
- Proper Sentry init function exists with FastAPI/Starlette integrations:
  - `agentflow_cli/src/app/core/config/sentry_config.py::init_sentry`
- `SENTRY_DSN` defined in settings; docs mention extras and configuration.
- `init_sentry()` is not invoked during app startup.

Recommended follow-ups:
- Call `init_sentry()` on startup (e.g., in `lifespan` or after app creation when DSN is present and extra installed).

## Additional highlight-worthy features

- Streaming graph execution: `/v1/graph/stream` for real-time output; invoke/get-state/stop APIs present.
  - Routers/services: `agentflow_cli/src/app/routers/graph/*`
- Checkpointer API: persist/merge/retrieve messages and state with well-typed schemas.
  - `agentflow_cli/src/app/routers/checkpointer/*`
- Store API: create/get/list/search/delete memory items via typed schemas.
  - `agentflow_cli/src/app/routers/store/*`
- Dependency Injection via InjectQ: container loaded and integrated into FastAPI for clean service/config injection.
  - `agentflow_cli/src/app/main.py`, `.../loader.py`
- Consistent error handling and response format: centralized exception handlers and uniform success/error envelopes.
  - `agentflow_cli/src/app/core/exceptions/handle_errors.py`, `agentflow_cli/src/app/utils/response_helper.py`
- Request tracing headers: Request ID and timestamp on every response.
  - `agentflow_cli/src/app/core/config/setup_middleware.py`

## Suggested quick wins to make claims fully true

- Sentry: invoke `init_sentry()` during startup when `SENTRY_DSN` is set.
- Docs: set `DOCS_PATH=/docs` and `REDOCS_PATH=/redoc` defaults or document enabling in deployment guide.
- Prometheus: add `/metrics` endpoint or middleware and document scrape config.
- Docker image: optionally implement `agentflow build --build` to run `docker build` after generating files.

## File pointers

- App: `agentflow_cli/src/app/main.py`
- Middleware: `agentflow_cli/src/app/core/config/setup_middleware.py`
- Logging: `agentflow_cli/src/app/core/config/setup_logs.py`
- Error handling: `agentflow_cli/src/app/core/exceptions/handle_errors.py`
- Auth: `agentflow_cli/src/app/core/auth/*`, `agentflow_cli/src/app/core/config/graph_config.py`
- Snowflake ID: `agentflow_cli/src/app/utils/snowflake_id_generator.py`, `.../core/config/settings.py`
- Sentry: `agentflow_cli/src/app/core/config/sentry_config.py`
- Graph/Checkpointer/Store routers and schemas: `agentflow_cli/src/app/routers/*`
- CLI entrypoints: `agentflow_cli/cli/main.py`, `agentflow_cli/cli/commands/*`
- Dockerfile generation: `agentflow_cli/cli/templates/defaults.py` and tests in `tests/cli/test_cli_commands_ops.py`
