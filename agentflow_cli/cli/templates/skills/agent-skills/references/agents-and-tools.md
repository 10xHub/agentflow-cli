# Agents and Tools

Use this when adding model behavior, tools, tool routing, provider options, retries, fallbacks, memory tools, or skills to an agent.

## Agent

`Agent` is a graph node that calls an LLM provider and appends the response to state. It supports OpenAI and Google provider flows behind a unified interface. Provider can be explicit (`"openai"` or `"google"`) or inferred from the model/config in existing code paths.

Common constructor concerns:

- `model`: model name.
- `provider`: provider name when auto-detection is not enough.
- `output_type`: `"text"`, `"image"`, `"video"`, or `"audio"`.
- `system_prompt`: string/list message instructions; supports `{state_field}` interpolation.
- `tool_node`: `ToolNode` instance or a graph node name string.
- `trim_context`: trims messages before model calls and writes summaries to `context_summary`.
- `reasoning_config`: effort/budget/provider reasoning options.
- `retry_config` and `fallback_models`: retry and cross-provider fallback behavior.
- `multimodal_config`: image/document/audio/video handling.
- `memory`: `MemoryConfig` that wires memory tools onto the tool node.
- `skills`: `SkillConfig` that discovers and exposes skills through the tool node.
- Extra kwargs such as `temperature`, `max_tokens`, and `base_url`.

## ToolNode

`ToolNode` registers and executes callable tools requested by the model. It supports local Python callables, MCP clients, Composio/LangChain style tools where supported by the implementation, and dynamically added tools.

For client-executed tools registered through `@10xscale/agentflow-client`, read `remote-tools.md`.

Tool authoring rules:

- Provide useful docstrings; they become model-facing descriptions.
- Provide type annotations; they become the parameter schema.
- Return plain values for normal tool results.
- Return `ToolResult` when a tool also needs to update state fields.
- Keep model-visible parameters separate from injected parameters.

Injected parameters are hidden from the model schema:

- `state`: current `AgentState` or subclass.
- `config`: execution config including `thread_id`, `user_id`, and `run_id`.
- `tool_call_id`: current model tool call ID.

## ReAct Loop

The standard tool-using graph loops from agent to tools and back:

1. `Agent` returns an assistant message.
2. Route to `ToolNode` when the last assistant message has `tools_calls`.
3. `ToolNode` appends a tool result message.
4. Route back to `Agent` so the model can produce a final answer.
5. End when there are no more tool calls.

## `@tool`

Use `agentflow.utils.tool` to add metadata such as name, description, tags, provider, capabilities, and arbitrary metadata. The decorator enriches the schema; it does not change injected parameter behavior.

## Source Map

- Agent implementation: `agentflow/agentflow/core/graph/agent.py`
- Tool node and graph exports: `agentflow/agentflow/core/graph`
- Tool result: `agentflow/agentflow/core/state/tool_result.py`
- Tool decorator: `agentflow/agentflow/utils/decorators.py`
- Skill integration: `agentflow/agentflow/core/skills`
- Prebuilt tools: `agentflow/agentflow/prebuilt/tools`
