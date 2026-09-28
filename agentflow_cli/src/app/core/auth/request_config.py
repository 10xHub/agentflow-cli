"""Keep server-owned keys out of client-supplied request ``config``.

Request ``config`` is an open dict on purpose: frontends pass their own values through it and
graph nodes and tools read them. Its keys cannot be allow-listed, because the API does not know
what an application sends.

A small set of keys is owned by the server instead, and a client must never set them:

- ``authz``   -- the isolation policy and scopes; the trusted copy lives in ``user["authz"]``
- ``user``    -- the verified identity
- ``user_id`` -- derived from the verified identity
- ``_*``      -- framework internals (``_skip_interrupt_at``, ``_node_name``, ...)

Every route and service that forwards client config to the graph, checkpointer or store must
pass it through :func:`client_config` first, then set the server-owned keys itself.

The thread a request runs on is also server-controlled: routes use the thread the permission
check approved, and both sides normalise it with :func:`normalize_thread_id`.
"""

from __future__ import annotations

from typing import Any


RESERVED_CONFIG_KEYS: frozenset[str] = frozenset({"authz", "user", "user_id"})
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


def normalize_thread_id(value: Any) -> str | None:
    """The one canonical form of a thread id, shared by the permission check and the services.

    Returns ``None`` for a missing or blank id, which means "start a new thread".
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None
