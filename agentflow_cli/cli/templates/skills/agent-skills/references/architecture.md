# Architecture

Use this when deciding where a change belongs or explaining how Agentflow packages interact. Check https://agentflow.10xscale.ai/ first for public package names.

---

## Published packages

| Public package | Registry | Install | Source |
|---|---|---|---|
| `10xscale-agentflow` | PyPI | `pip install 10xscale-agentflow` | `agentflow/agentflow` |
| `10xscale-agentflow-cli` | PyPI | `pip install 10xscale-agentflow-cli` | `agentflow-api/agentflow_cli` |
| `@10xscale/agentflow-client` | npm | `npm install @10xscale/agentflow-client` | `agentflow-client/src` |

---

## Layer responsibilities

### `10xscale-agentflow` — core Python library

| Sub-package | Key exports |
|---|---|
| `agentflow.core` | `StateGraph`, `Agent`, `ToolNode`, `AgentState`, `Message`, `StreamChunk` |
| `agentflow.prebuilt.agent` | `ReactAgent`, `PlanActReflectAgent`, `StructuredOutputAgent`, `SupervisorTeamAgent`, `SwarmAgent`, `RAGAgent` |
| `agentflow.prebuilt.tools` | `fetch_url`, `safe_calculator`, `file_read`, `file_write`, `file_search`, `google_web_search`, `vertex_ai_search`, `memory_tool`, `create_handoff_tool` |
| `agentflow.storage.checkpointer` | `InMemoryCheckpointer`, `PgCheckpointer` |
| `agentflow.storage.store` | `QdrantStore`, `Mem0Store` |
| `agentflow.storage.media` | `InMemoryMediaStore`, `LocalFileMediaStore`, `CloudMediaStore` |
| `agentflow.runtime` | Publisher adapters (SSE, A2A, Kafka, RabbitMQ, Redis Pub/Sub) |
| `agentflow.utils` | `ResponseGranularity`, `CallbackManager`, `tool` decorator |
| `agentflow.qa` | Testing helpers and evaluation tools |

### `10xscale-agentflow-cli` — API and CLI

Owns `agentflow api`, `agentflow play`, `agentflow init`, `agentflow build`, REST routers, auth/middleware, config loading, and graph service execution.

### `@10xscale/agentflow-client` — TypeScript HTTP client

Typed methods for invoke, stream, threads, memory store, file uploads, graph metadata, remote tools, and auth helpers. Calls a running Agentflow API server — does not run Python graphs.

---

## Request flow: invoke

1. `@10xscale/agentflow-client` or another HTTP caller sends messages plus `config.thread_id`.
2. FastAPI receives the request through auth and routers.
3. `GraphService` invokes against the compiled graph loaded at startup.
4. The compiled graph loads state from the checkpointer when `thread_id` exists.
5. Graph nodes run and update `AgentState`.
6. Checkpointer saves state, messages, and thread metadata.
7. API returns JSON to the caller.

## Request flow: stream

Identical through authentication and state loading. The difference: the graph sends `StreamChunk` events incrementally via SSE. Each chunk carries `event` (`"message"`, `"state"`, `"error"`, or `"updates"`), and the response is a `StreamingResponse`.

---

## Key design decisions

| Decision | Rationale |
|---|---|
| Graph compiled once at startup | Avoids repeated module loading per request |
| `thread_id` in every request | Allows stateless servers to restore conversation history |
| Checkpointer is injected, not hardcoded | Graph code does not depend on the storage backend |
| Auth is middleware, not in the graph | Business logic stays separate from access control |
| `injectq` for service wiring | Nodes and tools declare dependencies declaratively; the runtime resolves them |

---

## Design rules

- Compile graphs once at startup for API serving.
- Keep graph code storage-agnostic; wire checkpointer/store/media/dependencies through compile arguments, `InjectQ`, or `agentflow.json`.
- Treat `thread_id` as the continuity key for conversation state.
- Treat long-term memory store records as cross-thread knowledge, not thread history.
- Keep auth and request permissions in API middleware/routers, not inside graph nodes.

---

## Source map

- Core graph: https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow/core/graph
- State/message models: https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow/core/state
- Checkpointers: https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow/storage/checkpointer
- Memory stores: https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow/storage/store
- Media stores: https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow/storage/media
- API routers: https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/src/app/routers
- TS client: https://github.com/10xHub/agentflow-client/blob/main/src/client.ts
- Concepts: https://agentflow.10xscale.ai/concepts/architecture
