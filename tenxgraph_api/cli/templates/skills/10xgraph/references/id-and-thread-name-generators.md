# ID and Thread Name Generators

Use this when changing API ID generation, Snowflake IDs, graph ID generators, or thread display-name generation.

## Python Graph ID Generators

Core graph ID generators live in `tenxgraph.utils`.

Built-ins:

- `DefaultIDGenerator`
- `UUIDGenerator`
- `BigIntIDGenerator`
- `TimestampIDGenerator`
- `IntIDGenerator`
- `HexIDGenerator`
- `ShortIDGenerator`
- `AsyncIDGenerator`

Pass to `StateGraph(id_generator=...)`.

## API Snowflake ID Generator

The API package includes a Snowflake-style ID generator for server-side/generated IDs.

Environment/config variables:

- `SNOWFLAKE_EPOCH`
- `SNOWFLAKE_NODE_ID`
- `SNOWFLAKE_WORKER_ID`
- `SNOWFLAKE_TIME_BITS`
- `SNOWFLAKE_NODE_BITS`
- `SNOWFLAKE_WORKER_BITS`

Use Snowflake IDs when deployment needs sortable, distributed, non-UUID identifiers.

## Thread Name Generator

Configure in `10xgraph.json`:

```json
{
  "thread_name_generator": "graph.thread_name_generator:MyNameGenerator"
}
```

The API uses the configured generator when creating or naming threads. If no generator is configured, a dummy/default generator may be used.

Keep thread name generation:

- Fast enough for request paths.
- Safe for arbitrary user messages.
- Deterministic enough for tests where needed.

## Rules

- Keep ID type expectations aligned across Python state, API responses, checkpointers, and TypeScript client types.
- For multi-worker deployments, avoid process-local counters unless partitioned safely.
- Validate Snowflake node/worker bit settings before production use.
- Treat thread names as display labels, not stable identifiers.

## Source Map

- Python ID generators: https://github.com/10xGraph/10xGraph/blob/main/tenxgraph/utils/id_generator.py
- API Snowflake generator: https://github.com/10xGraph/10xgraph-api/blob/main/tenxgraph_api/src/app/utils/snowflake_id_generator.py
- Thread name generator: https://github.com/10xGraph/10xgraph-api/blob/main/tenxgraph_api/src/app/utils/thread_name_generator.py
- Graph service thread naming: https://github.com/10xGraph/10xgraph-api/blob/main/tenxgraph_api/src/app/routers/graph/services/graph_service.py
- Settings: https://github.com/10xGraph/10xgraph-api/blob/main/tenxgraph_api/src/app/core/config/settings.py
- Docs: https://10xgraph.com/
