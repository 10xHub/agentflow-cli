# Graph API Documentation

This document describes the graph API endpoints that have been added to the PyAgenity API.

## Endpoints

### 1. Invoke Graph - `/v1/graph/invoke`

**Method:** POST

**Description:** Execute the graph with the provided input and return the final result.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, can you help me with something?"
    }
  ],
  "thread_id": "optional-thread-id",
  "recursion_limit": 10,
  "config": {}
}
```

**Response:**
```json
{
  "data": {
    "messages": [...],
    "status": "completed",
    "metadata": {
      "config": {...}
    }
  },
  "metadata": {
    "request_id": "...",
    "timestamp": "...",
    "message": "OK"
  }
}
```

### 2. Stream Graph - `/v1/graph/stream`

**Method:** POST

**Description:** Execute the graph with streaming output for real-time results.

**Request Body:**
Same as invoke endpoint, with optional `stream_mode` query parameter.

**Query Parameters:**
- `stream_mode` (optional): Stream mode ("values", "updates", "messages", etc.). Default: "values"

**Response:**
Server-Sent Events (SSE) stream with chunks in the following format:
```
data: {"chunk_type": "values", "data": {...}, "metadata": {...}}

data: [DONE]
```

## Architecture

The graph API follows the same structure as the auth module:

```
src/app/routers/graph/
├── __init__.py
├── router.py                 # Main router with endpoints
├── services/
│   ├── __init__.py
│   └── graph_service.py      # Business logic
└── schemas/
    ├── __init__.py
    └── graph_schemas.py      # Request/response schemas
```

### Key Components

1. **GraphService**: Injected service that handles graph execution using the CompiledGraph from the dependency injection container.

2. **Message Conversion**: Automatically converts dictionary messages to PyAgenity Message objects and vice versa for seamless integration.

3. **Error Handling**: Comprehensive error handling with HTTP exceptions and proper logging.

4. **Streaming Support**: Real-time streaming of graph execution results using Server-Sent Events.

## Usage Examples

### Invoke Example
```bash
curl -X POST "http://localhost:8000/v1/graph/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the weather like?"}],
    "thread_id": "conversation-1",
    "recursion_limit": 5
  }'
```

### Stream Example
```bash
curl -X POST "http://localhost:8000/v1/graph/stream?stream_mode=values" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "thread_id": "stream-1"
  }'
```

## Configuration

The graph is loaded from the configuration specified in `pyagenity.json`:

```json
{
  "graphs": {
    "agent": "graph.react:app",
    "checkpointer": "graph.react:checkpointer"
  }
}
```

The CompiledGraph is automatically injected into the GraphService via the dependency injection container configured in `main.py`.
