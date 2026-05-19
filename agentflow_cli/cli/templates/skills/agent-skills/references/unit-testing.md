# Unit Testing

Use this when writing fast, deterministic tests for AgentFlow agent graphs without making real LLM API calls. All helpers live in `agentflow.qa.testing`.

## TestAgent

Drop-in replacement for `Agent`. Returns predefined responses from a list, cycling when called more than once. Never calls an LLM.

```python
from agentflow.qa.testing import TestAgent

agent = TestAgent(
    model="test-model",           # compatibility only; ignored
    responses=["Response 1", "Response 2"],  # cycles on repeated calls
    tools=["get_weather"],        # optional; enables simulate_tool_calls
    simulate_tool_calls=False,    # True → first call returns tool-call message
)
```

Swap into an existing graph:

```python
test_agent = TestAgent(responses=["Mocked"])
graph.override_node("MAIN", test_agent)
app = graph.compile()
```

Build a minimal graph inline:

```python
from agentflow.core.graph import StateGraph
from agentflow.utils.constants import END

graph = StateGraph()
graph.add_node("MAIN", test_agent)
graph.set_entry_point("MAIN")
graph.add_edge("MAIN", END)
app = graph.compile()
```

Tool-call simulation — set `simulate_tool_calls=True` (or pass `tools`). First invocation returns a `tools_calls` message; subsequent invocations return responses:

```python
agent = TestAgent(responses=["Final answer."], tools=["get_weather"])
# call 1 → tool-call message requesting get_weather
# call 2 → "Final answer."
```

Assertion helpers:

```python
agent.assert_called()            # called at least once
agent.assert_called_times(2)     # called exactly n times
agent.assert_not_called()
agent.get_last_messages()        # message list from last call
agent.get_last_tools()           # tool specs from last call
agent.reset()                    # clear call_count and call_history
```

Attributes: `call_count: int`, `call_history: list[dict]` (each has `messages`, `tools`, `kwargs`).

## QuickTest

One-liner async factory for common test scenarios. All methods are `async` — require `@pytest.mark.asyncio`.

```python
from agentflow.qa.testing import QuickTest
```

**single_turn** — single user/agent exchange:

```python
result = await QuickTest.single_turn(
    agent_response="Paris.",
    user_message="Capital of France?",
    config=None,
)
```

**multi_turn** — multiple turns with accumulated history:

```python
result = await QuickTest.multi_turn(
    conversation=[
        ("Hello", "Hi there!"),
        ("What can you do?", "Many things."),
    ]
)
```

**with_tools** — agent that issues tool calls, then responds:

```python
result = await QuickTest.with_tools(
    query="Weather in London?",
    response="It is sunny.",
    tools=["get_weather"],
    tool_responses={"get_weather": "22°C"},
)
```

Builds a `MAIN → TOOL → MAIN → END` graph internally using `TestAgent(simulate_tool_calls=True)`.

**custom** — bring your own agent and optional graph setup:

```python
result = await QuickTest.custom(
    agent=my_test_agent,
    user_message="Run it",
    graph_setup=None,   # callable(graph) → graph for extra wiring
)
```

## TestResult

Returned by every `QuickTest` method. All assertion methods return `self` for chaining.

```python
result.assert_contains("Paris")
result.assert_not_contains("London")
result.assert_equals("Paris is the capital.")
result.assert_tool_called("get_weather")
result.assert_tool_called("get_weather", city="London")  # with specific kwargs
result.assert_tool_not_called("send_email")
result.assert_message_count(3)
result.assert_no_errors()
```

Attributes: `final_response: str`, `messages: list`, `tool_calls: list[dict]`, `state: dict`, `passed: bool`.

## MockToolRegistry

Registers sync or async mock tools and tracks every invocation. Pass `tools.get_tool_list()` to `ToolNode`.

```python
from agentflow.qa.testing import MockToolRegistry
from agentflow.core.graph import ToolNode

tools = MockToolRegistry()
tools.register("get_weather", lambda city: f"22°C in {city}")
tools.register_async("search_web", async_fn)

tool_node = ToolNode(tools.get_tool_list())
```

Call tracking:

```python
tools.was_called("get_weather")                    # bool
tools.call_count("get_weather")                    # int
tools.get_calls("get_weather")                     # list[dict] with "args" and "kwargs"
tools.get_last_call("get_weather")                 # dict or None

tools.assert_called("get_weather")
tools.assert_called_with("get_weather", city="London")
tools.assert_call_count("get_weather", 2)

tools.reset()    # clear history, keep functions
tools.clear()    # clear history and functions
```

## agentflow test CLI

Thin pytest wrapper. Reads defaults from `agentflow.json → "test"` section; CLI flags override config.

```bash
agentflow test                     # pytest auto-discovery from project root
agentflow test tests/unit          # target path
agentflow test --coverage          # adds --cov=. --cov-report=term-missing --cov-report=html:htmlcov
agentflow test --coverage --html   # opens htmlcov/index.html after run
agentflow test -k "weather"        # keyword filter forwarded to pytest
agentflow test -- -m "not integration" --tb=short   # raw pytest flags after --
```

`agentflow.json` configuration:

```json
{
  "test": {
    "path": "tests",
    "coverage": true,
    "coverage_threshold": 80
  }
}
```

Exit code mirrors pytest: 0 = all pass, 1 = failures or coverage below threshold.

## Rules

- Never use real `Agent` in unit tests; always swap with `TestAgent`.
- All `QuickTest` methods are async — use `@pytest.mark.asyncio`.
- Call `agent.reset()` and `tools.reset()` between test cases to prevent state bleed.
- Mark slow or live-provider tests with `@pytest.mark.integration` so they are excluded from fast CI runs (`agentflow test -- -m "not integration"`).
- `TestAgent(tools=[...])` auto-enables `simulate_tool_calls`; pair it with a real `ToolNode(tools.get_tool_list())` to exercise the full routing loop.

## Source Map

- TestAgent: https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/qa/testing/test_agent.py
- QuickTest / TestResult: https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/qa/testing/quick_test.py
- MockToolRegistry: https://github.com/10xHub/Agentflow/blob/main/agentflow/agentflow/qa/testing/mock_tools.py
- CLI test command: https://github.com/10xHub/Agentflow/blob/main/agentflow-api/agentflow_cli/cli/commands/test.py
