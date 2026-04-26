# Prebuilt Agents and Tools

Use this when a task asks for ready-made agent patterns, common tools, or multi-agent handoff.

## Public Surface

Import from `agentflow.prebuilt`, `agentflow.prebuilt.agent`, or `agentflow.prebuilt.tools`.

Prebuilt agents currently exported:

- `ReactAgent`: builds the standard agent/tool loop around `Agent` and `ToolNode`.
- `RouterAgent`: routes work to specialized agents or branches.
- `RAGAgent`: retrieval augmented graph pattern with retriever and synthesis nodes.

Prebuilt tools currently exported:

- `safe_calculator`
- `fetch_url`
- `file_read`
- `file_search`
- `file_write`
- `google_web_search`
- `vertex_ai_search`
- `memory_tool`
- `make_user_memory_tool`
- `make_agent_memory_tool`
- `create_handoff_tool`
- `is_handoff_tool`

Several experimental prebuilt agent modules exist in source but are not exported from `agentflow.prebuilt.agent.__all__`; do not document them as stable without checking source and main docs.

## Handoff

Use `create_handoff_tool(target_agent_name)` when a model should transfer control to another agent. Handoff tools follow the naming convention `transfer_to_<agent_name>` and return a graph navigation command.

Typical use:

1. Add handoff tools to the coordinator or specialist `ToolNode`.
2. Mention available transfers in the relevant agent prompt.
3. Route tool calls through the standard ReAct loop.
4. Handoff interception detects transfer tools and jumps to the target agent.

Use `Command(goto=...)` directly for explicit runtime routing when not using the handoff helper.

## Rules

- Prefer prebuilt agents for common patterns before hand-writing graph loops.
- Check constructor signatures in source before using less common options.
- Treat exported `__all__` names as the stable public surface.
- Use handoff for agent-to-agent delegation, not for ordinary function calls.
- Keep handoff target names aligned with graph node names.

## Source Map

- Exports: `agentflow/agentflow/prebuilt/__init__.py`
- Agents: `agentflow/agentflow/prebuilt/agent`
- Tools: `agentflow/agentflow/prebuilt/tools`
- Handoff tool: `agentflow/agentflow/prebuilt/tools/handoff.py`
- Main docs: `agentflow-docs/docs/reference/python/command-handoff.md`
- How-to: `agentflow-docs/docs/how-to/python/handoff-between-agents.md`
