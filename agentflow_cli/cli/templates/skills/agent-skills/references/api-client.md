# API and TypeScript Client

Use this when aligning REST routes, schemas, generated docs, or the TypeScript npm SDK. The public npm package is `@10xscale/agentflow-client`; install it with `npm install @10xscale/agentflow-client`.

Check current docs first:

- `agentflow-docs/docs/get-started/connect-client.md`
- `agentflow-docs/docs/beginner/call-from-typescript.md`
- `agentflow-docs/docs/concepts/architecture.md`

## API Routers

Active routers are included from `agentflow-api/agentflow_cli/src/app/routers/setup_router.py`:

- Graph router
- Checkpointer/thread router
- Store router
- Ping router
- Media/files router

Graph routes include:

- `POST /v1/graph/invoke`
- `POST /v1/graph/stream`
- `GET /v1/graph`
- `GET /v1/graph:StateSchema`
- `POST /v1/graph/stop`
- `POST /v1/graph/setup`
- `POST /v1/graph/fix`

Memory/file routes are summarized in their topic references.

## TypeScript SDK Facade

`AgentFlowClient` is exported by `@10xscale/agentflow-client`. Its source facade is `agentflow-client/src/client.ts`, and it wraps:

- Connectivity and metadata: `ping`, `graph`, `graphStateSchema`
- Execution: `invoke`, `stream`, `stopGraph`, `fixGraph`, `setup`
- Threads/messages: `threadState`, `updateThreadState`, `clearThreadState`, `threadDetails`, `threads`, `threadMessages`, `addThreadMessages`, `singleMessage`, `deleteMessage`, `deleteThread`
- Memory: `storeMemory`, `searchMemory`, `getMemory`, `updateMemory`, `deleteMemory`, `listMemories`, `forgetMemories`
- Files: `uploadFile`, `getFile`, `getFileInfo`, `getFileAccessUrl`, `getMultimodalConfig`
- Remote tools: `registerTool`, then `setup`

For remote tools, read `remote-tools.md`; that flow has a client-managed execution loop around `remote_tool_call` blocks.

## Request Conventions

- The client serializes `Message` instances to plain API payloads.
- Server expects message content as an array of content blocks.
- `message_id` is sent as a string; `"0"` lets the server generate/normalize where applicable.
- `recursion_limit` defaults to `25`.
- Streaming defaults to low response granularity in the client.

## Rules

- Use `@10xscale/agentflow-client` in user-facing examples and docs; use `agentflow-client/src` only when referring to repository source.
- The TypeScript SDK calls a running Agentflow API server. It does not import or execute Python graph code.
- Keep endpoint schema changes mirrored in `agentflow-client/src/endpoints`.
- Keep exports in `agentflow-client/src/index.ts` aligned when adding public types.
- Test both endpoint helpers and the `AgentFlowClient` facade for client-visible changes.

## Source Map

- Client facade: `agentflow-client/src/client.ts`
- Client endpoints: `agentflow-client/src/endpoints`
- Client message model: `agentflow-client/src/message.ts`
- API schemas/services: `agentflow-api/agentflow_cli/src/app/routers`
