---
name: agentflow
description: Expert guidance for building, debugging, and extending applications with AgentFlow (10xscale-agentflow). TRIGGER when: code imports from agentflow (e.g. `from agentflow import`, `StateGraph`, `Agent`, `ToolNode`, `AgentState`); user references `agentflow.json` or CLI commands (`agentflow init`, `agentflow api`, `agentflow play`, `agentflow build`, `agentflow skills`); user is building graph-based multi-agent workflows, tools, memory, checkpointing, or streaming with this framework. SKIP: generic Python or multi-agent questions not referencing agentflow; other frameworks (LangGraph, CrewAI, AutoGen) unless comparing.
---

# Agentflow Project Skill

Use this skill when working in an Agentflow project. Agentflow is a multi-agent framework that wraps official OpenAI and Google SDK capabilities behind a unified graph, agent, tool, state, storage, API, CLI, and TypeScript client interface.

Treat https://agentflow.10xscale.ai/ as the first source of truth for public package names, install commands, and user-facing behavior. Use implementation source after the docs establish the intended API.

## Workflow

1. Identify the published package or docs surface involved:
   - PyPI core Python SDK: `10xscale-agentflow` (`pip install 10xscale-agentflow`), source at https://github.com/10xHub/Agentflow/tree/main/agentflow/agentflow
   - PyPI API/CLI SDK: `10xscale-agentflow-cli` (`pip install 10xscale-agentflow-cli`), source at https://github.com/10xHub/Agentflow/tree/main/agentflow-api/agentflow_cli
   - npm TypeScript SDK: `@10xscale/agentflow-client` (`npm install @10xscale/agentflow-client`), source at https://github.com/10xHub/Agentflow/tree/main/agentflow-client/src
   - Main docs: https://agentflow.10xscale.ai/
   - Playground/UI: `agentflow play` command after installed cli

2. Read the matching reference file before changing behavior:

   ### Core Python SDK
   - Architecture and package flow: `.github/skills/agentflow/references/architecture.md`
   - Agent constructor, provider, reasoning, retry, fallback, output_schema: `.github/skills/agentflow/references/agents-and-tools.md`
   - Graph construction, nodes, edges, compile, interrupts, config keys: `.github/skills/agentflow/references/state-graph.md`
   - State, messages, and content blocks: `.github/skills/agentflow/references/state-and-messages.md`
   - Thread and checkpointing: `.github/skills/agentflow/references/checkpointing-and-threads.md`
   - Dependency injection (InjectQ): `.github/skills/agentflow/references/dependency-injection.md`
   - Multimodal files and media stores: `.github/skills/agentflow/references/media-and-files.md`
   - Long-term memory stores (MemoryConfig, QdrantStore, Mem0Store): `.github/skills/agentflow/references/memory-and-store.md`
   - Streaming, StreamChunk, SSE, ResponseGranularity: `.github/skills/agentflow/references/streaming.md`
   - Stream emitter for tool progress updates: `.github/skills/agentflow/references/stream-emitter.md`
   - Observability hooks, validators, and runtime jumps: `.github/skills/agentflow/references/callbacks-and-command.md`
   - Prebuilt agents (ReactAgent, PlanActReflectAgent, StructuredOutputAgent, SupervisorTeamAgent, SwarmAgent, RAGAgent) and tools: `.github/skills/agentflow/references/prebuilt-agents-and-tools.md`
   - Event publishers and A2A/ACP runtime protocols: `.github/skills/agentflow/references/publishers-and-runtime-protocols.md`
   - Context management, ID generation, and background tasks: `.github/skills/agentflow/references/context-id-background.md`
   - Provider internals and adapters: `.github/skills/agentflow/references/providers-and-adapters.md`
   - Prompt-injection and validation safety: `.github/skills/agentflow/references/security-and-validators.md`

   ### API/CLI SDK
   - CLI commands and generated project files: `.github/skills/agentflow/references/cli-commands.md`
   - `agentflow.json` and dependency loading: `.github/skills/agentflow/references/api-configuration.md`
   - API auth and authorization: `.github/skills/agentflow/references/auth-and-authorization.md`
   - API environment, settings, and middleware: `.github/skills/agentflow/references/api-settings-and-middleware.md`
   - Rate limiting (config, backends, headers, custom backend): `.github/skills/agentflow/references/rate-limiting.md`
   - REST routes and error behavior: `.github/skills/agentflow/references/rest-api-and-errors.md`
   - API Snowflake IDs and thread naming: `.github/skills/agentflow/references/id-and-thread-name-generators.md`
   - API server and deployment runtime: `.github/skills/agentflow/references/production-runtime.md`

   ### TypeScript client SDK
   - REST and TypeScript client surface: `.github/skills/agentflow/references/api-client.md`
   - Browser/client-side tool execution: `.github/skills/agentflow/references/remote-tools.md`
   - TypeScript auth helpers and structured errors: `.github/skills/agentflow/references/client-auth-and-errors.md`
   - TypeScript messages, invoke, and stream details: `.github/skills/agentflow/references/client-messages-invoke-stream.md`
   - TypeScript thread, memory, and file APIs: `.github/skills/agentflow/references/client-threads-memory-files.md`

   ### Testing and QA
   - Unit testing without LLM calls (TestAgent, QuickTest, MockToolRegistry, `agentflow test`): `.github/skills/agentflow/references/unit-testing.md`
   - Evaluation framework (EvalSet, criteria, AgentEvaluator, QuickEval, UserSimulator, `agentflow eval`): `.github/skills/agentflow/references/evaluation.md`
   - Testing helpers overview: `.github/skills/agentflow/references/testing-and-evaluation.md`

3. Prefer existing Agentflow abstractions over new custom wiring:
   - Build workflows with `StateGraph`, `Agent`, `ToolNode`, `AgentState`, and `Message`.
   - Use prebuilt agents (`ReactAgent`, `PlanActReflectAgent`, `StructuredOutputAgent`, `SupervisorTeamAgent`, `SwarmAgent`, `RAGAgent`) for common patterns before hand-writing graph loops.
   - Persist conversation state with checkpointers; use stores only for cross-thread memory.
   - Put business services in `InjectQ` instead of global variables.
   - Keep API/CLI graph modules storage-agnostic and wire dependencies through `agentflow.json`.

4. Verify against source when implementation details matter. Public names and expected behavior should match https://agentflow.10xscale.ai/; source under https://github.com/10xHub/Agentflow (core), https://github.com/10xHub/agentflow-cli (API/CLI), and https://github.com/10xHub/agentflow-client (TypeScript) explains how that behavior is implemented.

## Local Conventions

- A compiled graph is normally loaded once by the API server and reused per request.
- Public package naming matters: use `10xscale-agentflow`, `10xscale-agentflow-cli`, and `@10xscale/agentflow-client` in user-facing docs and examples, not repository folder names.
- Every persisted interaction should include `config.thread_id`.
- Tools need docstrings and type annotations so model-facing schemas are useful.
- Injectable tool and node parameters (`state`, `config`, `tool_call_id`) are hidden from the model schema.
- For production, avoid process-local storage for shared state; use durable checkpointer/store backends.
- Add observability or audit side effects by registering a `GraphLifecycleHook` on `CallbackManager` — do not wrap `ainvoke()` / `astream()` calls in application code to achieve the same result.
- `reasoning_config` is on by default at medium effort; disable explicitly with `reasoning_config=None` when not needed.
- Provider is auto-detected from the model name; use `base_url` for third-party OpenAI-compatible APIs (Ollama, DeepSeek, OpenRouter).
