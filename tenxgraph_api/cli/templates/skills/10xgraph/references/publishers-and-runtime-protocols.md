# Publishers and Runtime Protocols

Use this when adding observability events, external event buses, A2A integration, ACP, or runtime adapters.

## Publishers

Publisher exports live under `tenxgraph.runtime.publisher` and `tenxgraph.runtime`.

Core types:

- `EventModel`: event payload model.
- `Event`: event source enum.
- `EventType`: lifecycle/phase enum.
- `ContentType`: payload content enum.
- `BasePublisher`: abstract publisher interface.
- `publish_event`: helper used by runtime internals.

Implementations:

- `ConsolePublisher`
- `RedisPublisher`
- `KafkaPublisher`
- `RabbitMQPublisher`

Publishers receive structured events from graph/tool execution. Use them for tracing, monitoring, audit logs, and external streaming/event bus integrations.

`ConsolePublisher` is a dev/debug, opt-in publisher (use a real transport in production). It writes
to stdout by default; pass `ConsolePublisher({"use_logger": True})` to route events through the
`tenxgraph.publisher` logger instead of stdout.

Realtime adds an `Event.REALTIME` event source and a `ContentType.TRANSCRIPT` content type (see
`realtime.md`).

## Runtime Adapters

LLM adapters:

- `BaseConverter`
- `GoogleGenAIConverter`
- `OpenAIConverter`
- `OpenAIResponsesConverter`
- `ConverterType`

Tool adapters:

- `LangChainAdapter`
- `ComposioAdapter`

Use adapters when translating provider-native or third-party tool formats into 10xGraph messages, tool schemas, and execution results.

## A2A Runtime

A2A helpers live in `tenxgraph.runtime.protocols.a2a`.

Key helpers:

- `make_agent_card`
- `build_a2a_app`
- `create_a2a_server`
- `delegate_to_a2a_agent`
- `create_a2a_client_node`
- `AgentFlowExecutor`

The A2A extras require the optional `a2a-sdk` dependency. Keep imports lazy or guarded where the dependency may not be installed.

## ACP

ACP support is in `tenxgraph/runtime/protocols/acp.py`. Treat it as a runtime protocol surface and check source before extending because public docs are thinner than core graph docs.

## Rules

- Prefer publisher events for observability instead of ad hoc print/log statements in reusable runtime paths.
- Keep publisher config serializable and environment-friendly.
- Close publishers on shutdown when they own network connections.
- Do not require optional protocol dependencies at core import time.
- For A2A, distinguish serving a 10xGraph graph as an A2A app from delegating to another A2A agent.

## Source Map

- Runtime exports: https://github.com/10xGraph/10xGraph/blob/main/tenxgraph/runtime/__init__.py
- Publishers: https://github.com/10xGraph/10xGraph/tree/main/tenxgraph/runtime/publisher
- A2A protocol: https://github.com/10xGraph/10xGraph/tree/main/tenxgraph/runtime/protocols/a2a
- ACP protocol: https://github.com/10xGraph/10xGraph/blob/main/tenxgraph/runtime/protocols/acp.py
- Docs: https://10xgraph.com/
