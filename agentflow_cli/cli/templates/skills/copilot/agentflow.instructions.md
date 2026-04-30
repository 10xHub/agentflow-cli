---
applyTo: "**"
---

# Agentflow project instructions

This repo uses **Agentflow** — a multi-agent framework that wraps the official OpenAI and Google SDKs behind a unified graph, agent, tool, state, storage, API, CLI, and TypeScript-client interface.

When generating, refactoring, or debugging code in this repo, prefer Agentflow's own abstractions over hand-rolled equivalents.

Use these instructions together with the Agentflow skill bundle at `.github/skills/agentflow`.
When a task touches a specific subsystem, read the matching reference file under
`.github/skills/agentflow/references/` before changing behavior.

## Public package names (use these in user-facing examples)

- Python core SDK: `10xscale-agentflow` — `pip install 10xscale-agentflow` — source under `agentflow/agentflow`
- Python API/CLI SDK: `10xscale-agentflow-cli` — `pip install 10xscale-agentflow-cli` — source under `agentflow-api/agentflow_cli`
- TypeScript SDK: `@10xscale/agentflow-client` — `npm install @10xscale/agentflow-client` — source under `agentflow-client/src`
- Docs: `agentflow-docs/docs` (treat as the source of truth for public API names)
- Playground: `agentflow play` (after the CLI is installed)

Never use repository folder names (e.g. `agentflow-cli`) in install commands or user-facing docs — use the published package names above.

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

## Where to look when you need more detail

For deeper context on any subsystem, read the matching reference under `.github/skills/agentflow/references/` or `agentflow-docs/docs`:

- Architecture and package flow
- Agent and tool behavior, prebuilt agents
- Graph construction, state, messages, content blocks
- Threads, checkpointers, dependency injection
- Multimodal media, long-term memory stores
- Streaming, SSE, runtime publishers, A2A/ACP protocols
- API server, REST routes, auth, errors, settings, middleware
- Rate limiting: sliding-window config, memory/Redis/custom backends, response headers, 429 behavior: `references/rate-limiting.md`
- TypeScript client: invoke, stream, threads, memory, files, A2UI
- Observability, validators, graph lifecycle hooks (`GraphLifecycleHook`), and runtime jumps (`Command`): `references/callbacks-and-command.md`

## Verifying behavior

Public names and behavior should match `agentflow-docs/docs`. Implementation under `agentflow/`, `agentflow-api/`, and `agentflow-client/src/` shows *how* — only consult source after docs establish *what*.
