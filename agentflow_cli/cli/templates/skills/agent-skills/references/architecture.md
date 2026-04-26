# Architecture

Use this when deciding where a change belongs or explaining how Agentflow packages interact. Check `agentflow-docs/docs/concepts/architecture.md` and `agentflow-docs/docs/get-started/installation.md` first for public package names.

## Published Packages

| Public package | Registry | Install | Source |
| --- | --- | --- | --- |
| `10xscale-agentflow` | PyPI | `pip install 10xscale-agentflow` | `agentflow/agentflow` |
| `10xscale-agentflow-cli` | PyPI | `pip install 10xscale-agentflow-cli` | `agentflow-api/agentflow_cli` |
| `@10xscale/agentflow-client` | npm | `npm install @10xscale/agentflow-client` | `agentflow-client/src` |

## Layer Responsibilities

- `10xscale-agentflow`: Core Python SDK. Owns `StateGraph`, `Agent`, `ToolNode`, `AgentState`, `Message`, checkpointers, stores, media, prebuilt agents/tools, runtime publishers, QA helpers, and skills support.
- `10xscale-agentflow-cli`: Python API and CLI SDK. Owns `agentflow api`, `agentflow play`, `agentflow init`, `agentflow build`, routers, auth/middleware, config loading, and graph service execution.
- `@10xscale/agentflow-client`: TypeScript npm SDK. Owns typed methods for invoke, stream, threads, memory store, files, graph metadata, remote tools, and auth/request helpers. It calls a running Agentflow API server and does not run Python graphs.
- `agentflow-docs/docs`: Main user-facing docs, concepts, how-to guides, and reference material. Prefer these docs over legacy docs for public behavior.
- `agentflow-playground` / UI packages: Interactive graph and agent testing surfaces.

## Request Flow

1. `@10xscale/agentflow-client` or another HTTP caller sends messages plus `config.thread_id`.
2. FastAPI receives the request through auth and routers.
3. `GraphService` invokes or streams against the compiled graph loaded at startup.
4. The compiled graph loads state through the checkpointer when a `thread_id` exists.
5. Graph nodes run and update `AgentState`.
6. Checkpointer saves state/messages/thread metadata.
7. API returns JSON or SSE chunks to the client.

## Design Rules

- Compile graphs once at startup for API serving.
- Keep graph code storage-agnostic; wire checkpointer/store/media/dependencies through compile arguments, `InjectQ`, or `agentflow.json`.
- Treat `thread_id` as the continuity key for conversation state.
- Treat long-term memory store records as cross-thread knowledge, not thread history.
- Keep auth and request permissions in API middleware/routers, not inside graph nodes.

## Source Map

- Core graph: `agentflow/agentflow/core/graph`
- State/message models: `agentflow/agentflow/core/state`
- Checkpointers: `agentflow/agentflow/storage/checkpointer`
- Memory stores: `agentflow/agentflow/storage/store`
- Media stores/resolvers: `agentflow/agentflow/storage/media`
- API routers: `agentflow-api/agentflow_cli/src/app/routers`
- API loader/config: `agentflow-api/agentflow_cli/src/app/loader.py`, `agentflow-api/agentflow_cli/src/app/core/config`
- TS client facade: `agentflow-client/src/client.ts`

## Public Docs Map

- Package overview: `agentflow-docs/docs/concepts/architecture.md`
- Install commands and package roles: `agentflow-docs/docs/get-started/installation.md`
- API serving: `agentflow-docs/docs/get-started/expose-with-api.md`
- TypeScript client usage: `agentflow-docs/docs/get-started/connect-client.md` and `agentflow-docs/docs/beginner/call-from-typescript.md`
