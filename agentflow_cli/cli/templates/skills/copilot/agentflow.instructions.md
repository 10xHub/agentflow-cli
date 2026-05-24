---
applyTo: "**"
---

# Agentflow project instructions

This repo uses **Agentflow** — a multi-agent framework that wraps the official OpenAI and Google SDKs behind a unified graph, agent, tool, state, storage, API, CLI, and TypeScript-client interface.

When generating, refactoring, or debugging code in this repo, prefer Agentflow's own abstractions over hand-rolled equivalents.

## Public package names (use these in user-facing examples)

- Python core SDK: `10xscale-agentflow` — `pip install 10xscale-agentflow` — source under `agentflow/agentflow`
- Python API/CLI SDK: `10xscale-agentflow-cli` — `pip install 10xscale-agentflow-cli` — source under `agentflow-api/agentflow_cli`
- TypeScript SDK: `@10xscale/agentflow-client` — `npm install @10xscale/agentflow-client` — source under `agentflow-client/src`
- Docs: https://agentflow.10xscale.ai/ (source of truth for public API names)
- Playground: `agentflow play` (after the CLI is installed)

Never use repository folder names (e.g. `agentflow-cli`) in install commands or user-facing docs — use the published package names above.

## Architecture overview

Three published packages, one request flow:

1. `@10xscale/agentflow-client` or another HTTP caller sends messages with `config.thread_id`.
2. FastAPI (`10xscale-agentflow-cli`) receives the request through auth and routers.
3. `GraphService` invokes or streams against the compiled graph loaded at startup.
4. The compiled graph loads state through the checkpointer when a `thread_id` exists.
5. Graph nodes run and update `AgentState`.
6. Checkpointer saves state, messages, and thread metadata.
7. API returns JSON or SSE chunks to the caller.

Compile graphs once at startup. Keep graph code storage-agnostic; wire dependencies through compile arguments, `InjectQ`, or `agentflow.json`.

## Core abstractions to reach for

- Build workflows with `StateGraph`, `Agent`, `ToolNode`, `AgentState`, and `Message`.
- Persist conversation state with **checkpointers**. Use **stores** only for cross-thread memory.
- Inject business services through **`InjectQ`**, not module-level globals.
- Keep API/CLI graph modules storage-agnostic; wire dependencies via `agentflow.json`.
- Every persisted interaction must include `config.thread_id`.
- Tools need docstrings and type annotations so model-facing schemas are useful.
- Injectable parameters (`state`, `config`, `tool_call_id`) are hidden from the model schema.
- For production, avoid process-local storage for shared state — use durable checkpointer/store backends.
- Add observability, audit, or business-logic side effects by registering a `GraphLifecycleHook` on `CallbackManager` — do not wrap `ainvoke()` / `astream()` calls in application code to achieve the same result.

## Key configuration (`agentflow.json`)

```json
{
  "agent": "graph.agent:app",
  "env": ".env",
  "auth": null,
  "checkpointer": null,
  "injectq": null,
  "store": null,
  "redis": null,
  "thread_name_generator": null
}
```

Set `"auth": {"method": "jwt"}` and `JWT_SECRET_KEY` in `.env` to enable JWT authentication.

## Important conventions

- A compiled graph is loaded once at API startup and reused per request.
- `thread_id` is the continuity key for conversation state — always pass it for persisted interactions.
- Auth and request permissions belong in API middleware/routers, not inside graph nodes.
- Long-term memory store records are cross-thread knowledge, not thread history.
- Rate limiting config lives in `agentflow.json` under `"rate_limit"`: backend options are `"memory"` or `"redis"`.

## Verifying behavior

Public names and behavior should match `agentflow-docs/docs` or https://agentflow.10xscale.ai/. Implementation under `agentflow/`, `agentflow-api/`, and `agentflow-client/src/` shows *how* — only consult source after docs establish *what*.
