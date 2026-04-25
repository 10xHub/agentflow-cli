---
name: agent-skills
description: Use for building, debugging, documenting, or extending Agentflow agents, tools, graphs, API/CLI services, TypeScript clients, memory, checkpointing, streaming, media, dependency injection, production runtime, and multi-agent workflows in this repository.
metadata:
  resources:
    - references/architecture.md
    - references/agents-and-tools.md
    - references/state-graph.md
    - references/state-and-messages.md
    - references/checkpointing-and-threads.md
    - references/dependency-injection.md
    - references/media-and-files.md
    - references/memory-and-store.md
    - references/streaming.md
    - references/production-runtime.md
    - references/api-client.md
    - references/remote-tools.md
    - references/callbacks-and-command.md
  tags:
    - agentflow
    - agents
    - multi-agent
    - framework
  priority: 10
---

# Agentflow Project Skill

Use this skill when working in this Agentflow monorepo. Agentflow is a multi-agent framework that wraps official OpenAI and Google SDK capabilities behind a unified graph, agent, tool, state, storage, API, CLI, and TypeScript client interface.

Treat `agentflow-docs/docs` as the first source of truth for public package names, install commands, and user-facing behavior. Use implementation source after the docs establish the intended API.

## Workflow

1. Identify the published package or docs surface involved:
   - PyPI core Python SDK: `10xscale-agentflow` (`pip install 10xscale-agentflow`), source in `agentflow/agentflow`
   - PyPI API/CLI SDK: `10xscale-agentflow-cli` (`pip install 10xscale-agentflow-cli`), source in `agentflow-api/agentflow_cli`
   - npm TypeScript SDK: `@10xscale/agentflow-client` (`npm install @10xscale/agentflow-client`), source in `agentflow-client/src`
   - Main docs: `agentflow-docs/docs`
   - Playground/UI: `agentflow play` command after installed cli
   
2. Read the matching reference file before changing behavior:
   - Architecture and package flow: `references/architecture.md`
   - Agent and tool behavior: `references/agents-and-tools.md`
   - Graph construction and execution: `references/state-graph.md`
   - State, messages, and content blocks: `references/state-and-messages.md`
   - Threads and persistence: `references/checkpointing-and-threads.md`
   - Dependency injection: `references/dependency-injection.md`
   - Multimodal files and media stores: `references/media-and-files.md`
   - Long-term memory stores: `references/memory-and-store.md`
   - Streaming, chunks, and SSE: `references/streaming.md`
   - API server and deployment runtime: `references/production-runtime.md`
   - REST and TypeScript client surface: `references/api-client.md`
   - Browser/client-side tool execution: `references/remote-tools.md`
   - Observability hooks, validators, and runtime jumps: `references/callbacks-and-command.md`
3. Prefer existing Agentflow abstractions over new custom wiring:
   - Build workflows with `StateGraph`, `Agent`, `ToolNode`, `AgentState`, and `Message`.
   - Persist conversation state with checkpointers; use stores only for cross-thread memory.
   - Put business services in `InjectQ` instead of global variables.
   - Keep API/CLI graph modules storage-agnostic and wire dependencies through `agentflow.json`.
4. Verify against source when implementation details matter. Public names and expected behavior should match `agentflow-docs/docs`; source under `agentflow/`, `agentflow-api/`, and `agentflow-client/src/` explains how that behavior is implemented.

## Local Conventions

- A compiled graph is normally loaded once by the API server and reused per request.
- Public package naming matters: use `10xscale-agentflow`, `10xscale-agentflow-cli`, and `@10xscale/agentflow-client` in user-facing docs and examples, not repository folder names.
- Every persisted interaction should include `config.thread_id`.
- Tools need docstrings and type annotations so model-facing schemas are useful.
- Injectable tool and node parameters such as `state`, `config`, and `tool_call_id` are hidden from the model schema.
- For production, avoid process-local storage for shared state; use durable checkpointer/store backends.
