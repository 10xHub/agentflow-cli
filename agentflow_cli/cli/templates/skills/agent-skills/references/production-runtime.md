# Production Runtime

Use this when changing API serving, deployment, auth/middleware, worker scaling, environment config, or Docker generation.

## API Server

`agentflow api` starts a Uvicorn ASGI server with FastAPI. The server loads the configured compiled graph once at startup and reuses it for requests.

Runtime components:

- Uvicorn ASGI process.
- FastAPI app.
- Auth and permission middleware.
- Routers for graph, threads/checkpointer, store, ping, and files.
- `GraphService` for invoke/stream/stop/setup/fix operations.
- Configured checkpointer, store, media store, and DI container.

## Async Execution

The API runtime handles sync and async graph nodes. Blocking model calls should not block the FastAPI event loop; service/runtime code schedules appropriately.

## Multi-worker Rules

- Use durable/shared storage when multiple worker processes serve the same graph.
- `InMemoryCheckpointer` is process-local and unsuitable for load-balanced continuity.
- Use `PgCheckpointer` or equivalent durable backend for shared state.
- Use shared memory/media stores when clients can hit any worker.

## Environment Configuration

Important variables include:

- `MODE`: development or production.
- `LOG_LEVEL`
- `ORIGINS`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `REDIS_URL`
- `GRAPH_PATH`: path to `agentflow.json`; defaults to `agentflow.json`.

Production should set `MODE=production`, configure CORS origins, and use real auth secrets.

## CLI and Docker

- `agentflow api`: serve graph over HTTP.
- `agentflow play`: serve graph and open/use playground flow.
- `agentflow init`: scaffold config and graph.
- `agentflow build --docker-compose`: generate Docker deployment files.

## Source Map

- App startup: `agentflow-api/agentflow_cli/src/app/main.py`
- Route setup: `agentflow-api/agentflow_cli/src/app/routers/setup_router.py`
- Graph service: `agentflow-api/agentflow_cli/src/app/routers/graph/services`
- Config/middleware/auth: `agentflow-api/agentflow_cli/src/app/core`
- CLI commands: `agentflow-api/agentflow_cli/cli`
