# Remote Tools

Use this when implementing tools that execute in a TypeScript client or browser process while the Python graph runs on the Agentflow API server.

## Concept

Remote tools let a graph advertise a tool schema to the model while deferring execution to the client. The server returns a `RemoteToolCallBlock` instead of executing the tool locally. The TypeScript SDK detects that block, runs the registered handler, sends back a `ToolResultBlock`, and continues the invoke or stream loop.

Use remote tools for:

- Browser-only capabilities such as DOM access, local files selected by the user, Web APIs, or UI state.
- Client-owned integrations that should not expose credentials to the server.
- Tools whose implementation belongs with the app using `@10xscale/agentflow-client`.

Use local Python tools, MCP, Composio, or LangChain tools when execution should happen server-side.

## Registration Flow

1. In TypeScript, call `client.registerTool({ node, name, description, parameters, handler })`.
2. Call `await client.setup()` before invoking the graph.
3. The client posts remote tool schemas to `POST /v1/graph/setup`.
4. The API groups tools by `node_name` and calls `CompiledGraph.attach_remote_tools(tools, node_name)`.
5. The relevant Python `ToolNode` marks those names as remote.

Remote tool schema shape:

```typescript
{
  node_name: "TOOLS",
  name: "read_browser_state",
  description: "Read selected browser state.",
  parameters: {
    type: "object",
    properties: {},
    required: []
  }
}
```

## Execution Flow

1. Model requests a tool call.
2. `ToolNode` sees the tool name in `remote_tool_names`.
3. Instead of executing locally, the server returns a `Message` with `RemoteToolCallBlock`.
4. TypeScript `invoke` or `stream` detects content blocks with `type === "remote_tool_call"`.
5. `ToolExecutor.executeToolCalls` runs matching registered handlers.
6. The client creates `Message.tool_message([ToolResultBlock(...)] )`.
7. The client sends tool result messages in the next API iteration.

The client controls the recursion loop and stops when no remote tool calls remain or when `recursion_limit` is reached.

## Important Types

Python:

- `RemoteToolCallBlock`: `agentflow/agentflow/core/state/message_block.py`
- `ToolResultBlock`: same module
- `ToolNode.remote_tool_names`: checked during tool execution

TypeScript:

- `RemoteTool`: `agentflow-client/src/endpoints/setupGraph.ts`
- `ToolRegistration`: `agentflow-client/src/tools.ts`
- `ToolExecutor`: `agentflow-client/src/tools.ts`
- `RemoteToolCallBlock`: `agentflow-client/src/message.ts`

## Rules

- `node` / `node_name` must match the graph tool node that should expose the remote tools.
- `name` must match the tool call name the model will emit.
- `parameters` should be JSON-schema-like and precise; this schema is model-facing.
- Register tools and call `client.setup()` before `invoke` or `stream`.
- Return serializable values from TypeScript handlers so they can be placed in `ToolResultBlock.output`.
- Handle missing tools and handler errors as tool result errors, not transport failures.

## Source Map

- API setup schema: `agentflow-api/agentflow_cli/src/app/routers/graph/schemas/graph_schemas.py`
- API setup route: `agentflow-api/agentflow_cli/src/app/routers/graph/router.py`
- API setup service: `agentflow-api/agentflow_cli/src/app/routers/graph/services/graph_service.py`
- Python block model: `agentflow/agentflow/core/state/message_block.py`
- Python remote handling: `agentflow/agentflow/core/graph/tool_node/base.py`
- TS setup endpoint: `agentflow-client/src/endpoints/setupGraph.ts`
- TS invoke loop: `agentflow-client/src/endpoints/invoke.ts`
- TS stream loop: `agentflow-client/src/endpoints/stream.ts`
- TS executor: `agentflow-client/src/tools.ts`
