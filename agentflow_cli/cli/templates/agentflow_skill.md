# AgentFlow

This project uses **AgentFlow** (`10xscale-agentflow`) — a graph-based Python
framework for building LLM agents. Use this guide when writing or modifying
agent code in this repo.

## When to use AgentFlow primitives

- **`StateGraph`** — the top-level container. Nodes run, edges decide what runs next.
- **`Agent`** — a node that calls an LLM. Handles provider SDKs, tool routing, memory, retries.
- **`ToolNode`** — a node that executes Python functions when the LLM requests tool calls.
- **`AgentState`** / **`Message`** — conversation state and messages flowing through the graph.
- **`InMemoryCheckpointer`** / other checkpointers — persist state per `thread_id`.

Don't reach for raw provider SDKs (`openai`, `google-genai`) inside a graph node.
Use `Agent` with the right `provider=` instead — it handles message conversion,
streaming, tool calls, retries, and fallbacks uniformly.

## Golden-path ReAct agent

```python
from dotenv import load_dotenv

from agentflow.core import Agent, StateGraph, ToolNode
from agentflow.core.state import AgentState, Message
from agentflow.storage.checkpointer import InMemoryCheckpointer
from agentflow.utils.constants import END

load_dotenv()


def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is sunny"


tool_node = ToolNode([get_weather])

agent = Agent(
    model="gpt-4o",
    provider="openai",
    system_prompt=[{"role": "system", "content": "You are a helpful assistant."}],
    tool_node=tool_node,
)


def should_use_tools(state: AgentState) -> str:
    last = state.context[-1] if state.context else None
    if last and getattr(last, "tools_calls", None) and last.role == "assistant":
        return "TOOL"
    if last and last.role == "tool":
        return "MAIN"
    return END


graph = StateGraph()
graph.add_node("MAIN", agent)
graph.add_node("TOOL", tool_node)
graph.add_conditional_edges("MAIN", should_use_tools, {"TOOL": "TOOL", END: END})
graph.add_edge("TOOL", "MAIN")
graph.set_entry_point("MAIN")

app = graph.compile(checkpointer=InMemoryCheckpointer())

# Invoke with a stable thread_id to get persistent history
res = app.invoke(
    {"messages": [Message.text_message("What is the weather in NYC?")]},
    config={"thread_id": "demo", "recursion_limit": 10},
)
```

## Providers

Pick a provider via the `provider=` argument on `Agent`. Model names are free-form strings.

| Provider | Auth | Models |
|---|---|---|
| `"openai"` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3`, `o4-mini` |
| `"google"` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-2.5-pro` |
| `"vertex_ai"` | `GOOGLE_CLOUD_PROJECT` + Application Default Credentials | same Gemini models |

Rules:

- If `provider` is omitted, it is inferred: `gpt*|o1|o3|o4` → `openai`, `gemini*` → `google`.
- `vertex_ai` is **never** inferred — set it explicitly.
- `google` and `vertex_ai` share model names and features; only auth differs.
- `google-genai` is not bundled. Install it when using either Gemini path:
  `pip install google-genai`.

## Agent parameters worth knowing

```python
Agent(
    model="gpt-4o",
    provider="openai",
    system_prompt=[{"role": "system", "content": "..."}],
    tool_node=tool_node,                 # ToolNode instance or str name
    output_type="text",                  # "text" | "json"
    trim_context=True,                   # trim to model context window
    reasoning_config=True,               # enable extended thinking (o1/o3/gemini-2.5)
    retry_config=True,                   # retry transient API errors
    fallback_models=[                    # try these if primary fails
        "gpt-4o-mini",
        ("gemini-2.5-flash", "google"),
    ],
    memory=my_memory_config,             # long-term memory retrieval
    skills=my_skill_config,              # inject skill documents
    multimodal_config=my_mm_config,      # auto-offload large inline media
)
```

## State & messages

- Custom state extends `AgentState`:

  ```python
  class MyState(AgentState):
      user_id: str | None = None
  ```

- `Message.text_message("...")` builds a user message quickly.
- Tool functions can accept `tool_call_id: str` and `state: MyState` — they are
  injected automatically if declared.

## Checkpointing

- `InMemoryCheckpointer()` for dev / tests.
- `PgCheckpointer` / `RedisCheckpointer` for production
  (requires `REDIS_URL` or a Postgres DSN).
- Always pass `config={"thread_id": "..."}` on `invoke` / `stream` to keep
  history across calls.

## CLI

AgentFlow ships a CLI (`10xscale-agentflow-cli`):

- `agentflow init` — scaffold `agentflow.json` and `graph/react.py`.
- `agentflow api` — run the FastAPI server over your graph.
- `agentflow play` — start the API + open the hosted playground.
- `agentflow build` — generate a `Dockerfile` (optionally `docker-compose.yml`).
- `agentflow skill` — regenerate these coding-agent skill files.

`agentflow.json` points at the compiled graph (`"agent": "graph.react:app"`).

## Don't

- Don't call provider SDKs directly from a graph node. Use `Agent`.
- Don't mutate `state` in place — return a new state/messages from your node.
- Don't infer `vertex_ai` from the model name. Pass it explicitly.
- Don't commit API keys; keep them in `.env` (referenced by `agentflow.json`).
- Don't hand-roll retry loops around `Agent` — use `retry_config=True`.

## Where to look

- Python reference: `agentflow.core`, `agentflow.core.graph`, `agentflow.core.state`,
  `agentflow.storage.checkpointer`, `agentflow.utils.constants`.
- Runtime adapters (`GoogleGenAIConverter`, OpenAI converters) live under
  `agentflow.runtime.adapters.llm` — only needed when wrapping raw SDK calls.
