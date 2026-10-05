"""Keep server-owned keys out of client-supplied request ``config``.

Request ``config`` is an open dict on purpose: frontends pass their own values through it and
graph nodes and tools read them. Its keys cannot be allow-listed, because the API does not know
what an application sends.

A small set of keys is owned by the server instead, and a client must never set them:

- ``authz``   -- the isolation policy and scopes; the trusted copy lives in ``user["authz"]``
- ``user``    -- the verified identity
- ``user_id`` -- derived from the verified identity
- ``remote_tools`` -- per-run client tool schemas the model may call; only protocol adapters
  whose clients legitimately bring tools (AG-UI) set it, from the protocol's own tool list
- ``_*``      -- framework internals (``_skip_interrupt_at``, ``_node_name``, ...)

Every route and service that forwards client config to the graph, checkpointer or store must
pass it through :func:`client_config` first, then set the server-owned keys itself.

The thread a request runs on is also server-controlled: routes use the thread the permission
check approved, and both sides normalise it with :func:`normalize_thread_id`.

Tool calls are server-controlled too: only the model may request a tool. Client messages
are checked with :func:`client_tool_call_error`. A client may send a tool *result* only as the
answer to a remote tool call that is still waiting for one (:func:`unanswered_tool_calls`).
"""

from __future__ import annotations

from typing import Any


RESERVED_CONFIG_KEYS: frozenset[str] = frozenset({"authz", "user", "user_id", "remote_tools"})
INTERNAL_KEY_PREFIX = "_"


def _is_client_key(key: Any) -> bool:
    return (
        isinstance(key, str)
        and key not in RESERVED_CONFIG_KEYS
        and not key.startswith(INTERNAL_KEY_PREFIX)
    )


def client_config(config: Any) -> dict[str, Any]:
    """Return a copy of client-supplied config without server-owned keys.

    Application keys pass through unchanged, including ``thread_id``, which each route then
    replaces with, or checks against, the thread the permission check approved.
    """
    if not isinstance(config, dict):
        return {}
    return {key: value for key, value in config.items() if _is_client_key(key)}


# Content blocks that ask the server to run a tool. Only the model produces these; tool
# *results* (``tool_result``) are fine, since remote tools send them back from the client.
TOOL_CALL_BLOCK_TYPES: frozenset[str] = frozenset({"tool_call", "remote_tool_call"})


def _field(message: Any, name: str) -> Any:
    if isinstance(message, dict):
        return message.get(name)
    return getattr(message, name, None)


def client_tool_call_error(messages: Any) -> str | None:
    """Describe the first client-supplied message that carries a tool call, or ``None``.

    A ``ToolNode`` executes the ``tools_calls`` of the last message in context, so a client
    that can write a tool call can run any server tool with its own arguments, skipping the
    model, the system prompt and any guard node. Accepts ``Message`` objects or plain dicts.
    """
    if not isinstance(messages, list | tuple):
        return None
    for index, message in enumerate(messages):
        carries_call = bool(_field(message, "tools_calls")) or any(
            _field(block, "type") in TOOL_CALL_BLOCK_TYPES
            for block in _field(message, "content") or []
        )
        if carries_call:
            return f"messages[{index}] carries a tool call; only the model may request tools"
    return None


def tool_result_ids(messages: Any) -> list[str]:
    """The ``call_id`` of every tool result block in ``messages``, in order."""
    if not isinstance(messages, list | tuple):
        return []
    return [
        str(_field(block, "call_id"))
        for message in messages
        for block in _field(message, "content") or []
        if _field(block, "type") == "tool_result"
    ]


def _tool_calls(message: Any) -> list[tuple[str, str]]:
    """``(call_id, tool_name)`` for every tool call a message makes."""
    calls: list[tuple[str, str]] = []
    for call in _field(message, "tools_calls") or []:
        if isinstance(call, dict) and call.get("id"):
            name = (call.get("function") or {}).get("name") or call.get("name") or ""
            calls.append((str(call["id"]), str(name)))
    for block in _field(message, "content") or []:
        if _field(block, "type") in TOOL_CALL_BLOCK_TYPES and _field(block, "id"):
            calls.append((str(_field(block, "id")), str(_field(block, "name") or "")))
    return calls


def unanswered_tool_calls(context: Any) -> dict[str, str]:
    """Map ``call_id -> tool_name`` for the tool calls in ``context`` that have no result yet."""
    calls: dict[str, str] = {}
    for message in context or []:
        if _field(message, "role") == "assistant":
            for call_id, name in _tool_calls(message):
                calls.setdefault(call_id, name)
    for call_id in tool_result_ids(list(context or [])):
        calls.pop(call_id, None)
    return calls


def normalize_thread_id(value: Any) -> str | None:
    """The one canonical form of a thread id, shared by the permission check and the services.

    Returns ``None`` for a missing or blank id, which means "start a new thread".
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None
