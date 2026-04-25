# Callbacks and Command

Use this when adding validation, tracing, invocation hooks, error recovery, or runtime graph jumps.

## CallbackManager

`CallbackManager` registers hooks around AI, tool, MCP, input validation, and skill invocations.

Invocation types:

- `InvocationType.AI`
- `InvocationType.TOOL`
- `InvocationType.MCP`
- `InvocationType.INPUT_VALIDATION`
- `InvocationType.SKILL`

Hook families:

- `register_before_invoke(invocation_type, callback)`: validate or transform input before invocation.
- `register_after_invoke(invocation_type, callback)`: inspect or transform output after invocation.
- `register_on_error(invocation_type, callback)`: log, recover, or return a recovery `Message`.
- `register_input_validator(validator)`: add a `BaseValidator` that validates incoming messages.

Callbacks can be callable objects or functions and may be sync or async. Error callbacks should return a `Message` recovery value or `None`.

## Validators

Use `BaseValidator` for input validation. Implement:

```python
async def validate(self, messages: list[Message]) -> bool:
    ...
```

Register validators on a `CallbackManager`, then pass it to graph compilation:

```python
callback_manager = CallbackManager()
callback_manager.register_input_validator(MyValidator())

app = graph.compile(callback_manager=callback_manager)
```

Use validators for safety checks, business rules, input policy, and prompt-injection detection.

## Command

`Command` lets a node combine state/message updates with control flow. Use it when the next node depends on runtime logic inside the node and is awkward to express as a static conditional edge.

Fields:

- `update`: state update, `Message`, string, converter, or `None`.
- `goto`: next node name or `END`.
- `graph`: optional graph target; `Command.PARENT` is reserved for parent graph navigation patterns.
- `state`: optional attached state.

Prefer conditional edges for normal routing because they are easier to visualize and test. Use `Command(goto=...)` for dynamic jumps, recovery branches, handoffs, or side-effect-dependent routing.

## Patterns

Callback for tracing:

```python
from agentflow.utils.callbacks import CallbackContext, CallbackManager, InvocationType

async def trace_after(context: CallbackContext, input_data, output_data):
    print(context.invocation_type, context.node_name)
    return output_data

callback_manager = CallbackManager()
callback_manager.register_after_invoke(InvocationType.TOOL, trace_after)
app = graph.compile(callback_manager=callback_manager)
```

Command for dynamic routing:

```python
from agentflow.utils import Command, END

def router_node(state, config):
    if state.context[-1].text() == "stop":
        return Command(goto=END)
    return Command(update={"route": "repair"}, goto="REPAIR")
```

## Rules

- Keep callback side effects bounded; they run inside graph execution paths.
- Avoid storing per-request mutable state globally inside callbacks.
- Use `CallbackContext` metadata to distinguish node/function/invocation details.
- Return transformed data from callbacks only when the downstream invocation expects that shape.
- Use `Command` sparingly; static and conditional edges remain the default graph structure.
- Always test command routes for recursion limits and missing destination nodes.

## Source Map

- Callback system: `agentflow/agentflow/utils/callbacks.py`
- Default validators: `agentflow/agentflow/utils/validators.py`
- Graph compile callback argument: `agentflow/agentflow/core/graph/state_graph.py`
- Command API: `agentflow/agentflow/utils/command.py`
- Command execution paths: `agentflow/agentflow/core/graph/compiled_graph.py`
- Legacy docs: `agentflow-docs/docs-mkdocs-legacy/reference/library/Command.md`
