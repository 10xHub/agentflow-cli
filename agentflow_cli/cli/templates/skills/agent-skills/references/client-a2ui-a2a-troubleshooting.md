# Client A2UI, A2A, and Troubleshooting

Use this when changing TypeScript WebSocket UI integration, agent-to-agent client types, or npm SDK troubleshooting guidance.

## A2UI WebSocket Client

A2UI code lives under `agentflow-client/src/a2ui`.

Exports:

- `A2UIClient`
- `createA2UIClient`
- `A2UIClientConfig`
- `A2UIMessage`
- `A2UIMessageType`
- `ConnectionState`
- React hooks from `hooks.ts`

Client config:

- `baseUrl`
- `agentId`
- `authToken`
- `reconnect`
- `reconnectInterval`
- `maxReconnectAttempts`
- `debug`

The client converts `http`/`https` base URLs to `ws`/`wss` and connects to `/ws/agents/{agentId}`. If `authToken` is provided, it is sent as a `token` query parameter.

Message types:

- `AGENT_STATUS`
- `AGENT_MESSAGE`
- `AGENT_THINKING`
- `AGENT_ERROR`
- `AGENT_COMPLETE`
- `AGENT_TOOL_CALL`
- `AGENT_TOOL_RESULT`
- `*` wildcard

React hooks:

- `useA2UIClient`
- `useAgentStatus`
- `useAgentMessages`
- `useAgentThinking`
- `useAgentCommunication`
- `useA2UIMessage`

## A2A / ACP TypeScript Client

A2A code lives in `agentflow-client/src/endpoints/a2a.ts` and `agentflow-client/src/types/a2a.ts`.

Important types:

- `A2AClient`
- `ACPMessage`
- `ACPMessageType`
- `MessageContent`
- `MessageContext`
- `AgentRegistryEntry`
- `SendMessageParams`
- `BroadcastMessageParams`
- `NotificationParams`
- `AgentStatusUpdate`
- `AgentMessageEvent`

Client methods include agent registration, unregistering, direct messages, broadcasts, notifications, agent listing/status, and heartbeat-style flows.

Important caution: A2A API server routes in `agentflow-api` appear commented or experimental in places. Before documenting as stable or relying on it, check current server route registration and tests.

## Client Troubleshooting

Common issue map:

- Every request fails immediately: check `baseUrl`, server running status, network, timeout.
- Browser fails but curl works: check CORS, credentials, auth headers, HTTPS/mixed content.
- Thread continuity broken: ensure the same `config.thread_id` is reused and checkpointer is configured.
- Stream differs from invoke: inspect `response_granularity`, SSE support, proxy buffering, and stream event handling.
- Remote tools do nothing: call `client.setup()`, match tool `node` to graph node name, and check handler errors.
- Auth failures: align server `auth` config with client `auth`, `authToken`, or headers.

## Package and Build Surface

Package:

- npm name: `@10xscale/agentflow-client`
- ESM package: `"type": "module"`
- Node engine: `>=18.0.0`
- Published files: `dist`, `README.md`, `LICENSE`

Scripts:

- `npm run build`
- `npm run test:run`
- `npm run test`
- `npm run coverage`

Public exports are controlled by `agentflow-client/src/index.ts`; update it when adding public endpoint/type files.

## Rules

- Treat A2UI and A2A as separate from the main REST `AgentFlowClient`.
- Verify server-side routes exist before marking A2A/A2UI behavior stable.
- Keep React hooks free of server-specific assumptions beyond the WebSocket message contract.
- Keep troubleshooting docs close to real browser failure modes: CORS, cookies, auth headers, proxy buffering, and timeouts.
- Keep package exports and generated declaration files in sync.

## Source Map

- A2UI client: `agentflow-client/src/a2ui/client.ts`
- A2UI hooks: `agentflow-client/src/a2ui/hooks.ts`
- A2UI types: `agentflow-client/src/a2ui/types.ts`
- A2A client: `agentflow-client/src/endpoints/a2a.ts`
- A2A types: `agentflow-client/src/types/a2a.ts`
- Public exports: `agentflow-client/src/index.ts`
- Package manifest: `agentflow-client/package.json`
- Docs: `agentflow-docs/docs/troubleshooting/client.md`
