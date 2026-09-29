"""Declarative description of every ``agentflow.json`` option the editor shows.

The browser page renders itself from :func:`build_schema`, so adding a new
configuration key only needs a new entry here (plus a rule in ``validation``).

Section shape::

    {
        "id": "rate_limit",  # stable id, used by validation issues
        "title": "Rate limiting",
        "description": "...",
        "key": "rate_limit",  # top-level key, or None for root-level fields
        "optional": True,  # renders an on/off toggle for the whole key
        "off_summary": "...",  # what happens while the key is absent
        "default": {...},  # value written when the toggle is switched on
        "widget": None,  # custom renderer: "auth", "authorization", "remote_tools"
        "fields": [...],  # generic fields, paths are relative to the root
        "notes": ["..."],  # extra hints (secrets that belong in .env, ...)
    }

Field shape::

    {
        "path": ["rate_limit", "redis", "url"],
        "label": "Redis URL",
        "type": "text" | "number" | "bool" | "select" | "list",
        "help": "...",
        "placeholder": "...",
        "options": [...],  # select only
        "min": 0,
        "step": 1,  # number only
        "required": False,
        "default": ...,  # value the server assumes when the key is absent
        "group": "Backend",  # fields sharing a group render together
        "show_if": {"path": [...], "equals": value},
    }
"""

from __future__ import annotations

import copy
from typing import Any


DOCS_URL = "https://agentflow.10xscale.ai/docs/reference/api-cli/configuration"

# Mirrors authorization.all_scopes(); kept in sync by a unit test so the
# editor never imports the core framework just to render suggestions.
AUTHORIZATION_SCOPES: tuple[str, ...] = (
    "checkpointer:delete",
    "checkpointer:read",
    "checkpointer:write",
    "config:read",
    "files:read",
    "files:upload",
    "graph:fix",
    "graph:invoke",
    "graph:read",
    "graph:setup",
    "graph:stop",
    "graph:stream",
    "store:delete",
    "store:read",
    "store:write",
)

BUILTIN_AUTHORIZATION: tuple[str, ...] = ("ownership", "allow_all", "default", "none")

# Keys read by the CLI or the API server. Anything else is preserved but flagged.
KNOWN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "agent",
        "env",
        "auth",
        "authorization",
        "rate_limit",
        "websocket",
        "ag_ui",
        "observability",
        "injectq",
        "store",
        "checkpointer",
        "thread_name_generator",
        "redis",
        "remote_tools",
        "test",
        "evaluation",
    }
)

_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "core",
        "title": "Core",
        "description": "The compiled graph the server runs and the dotenv file it loads.",
        "key": None,
        "optional": False,
        "fields": [
            {
                "path": ["agent"],
                "label": "Agent graph",
                "type": "text",
                "required": True,
                "placeholder": "graph.react:app",
                "help": "Import path of the compiled graph, as module:attribute.",
            },
            {
                "path": ["env"],
                "label": "Env file",
                "type": "text",
                "placeholder": ".env",
                "help": "Dotenv file loaded before the graph starts. Leave empty to skip.",
            },
        ],
    },
    {
        "id": "auth",
        "title": "Authentication",
        "description": "Who is calling the API. Leave off for local development.",
        "key": "auth",
        "optional": True,
        "off_summary": "Every request is accepted without authentication.",
        "default": "jwt",
        "widget": "auth",
        "fields": [],
        "notes": [
            "JWT needs JWT_SECRET_KEY and JWT_ALGORITHM in your .env file.",
            "Custom auth points at a BaseAuth subclass, as module:attribute.",
        ],
    },
    {
        "id": "authorization",
        "title": "Authorization",
        "description": (
            "What an authenticated user may do. When off, production uses ownership "
            "and development allows everything."
        ),
        "key": "authorization",
        "optional": True,
        "off_summary": "Production enforces ownership checks; development allows everything.",
        "default": "ownership",
        "widget": "authorization",
        "fields": [],
        "scopes": list(AUTHORIZATION_SCOPES),
    },
    {
        "id": "rate_limit",
        "title": "Rate limiting",
        "description": "Sliding-window request limits applied to every REST call.",
        "key": "rate_limit",
        "optional": True,
        "off_summary": "Requests are not rate limited.",
        "default": {
            "enabled": True,
            "backend": "memory",
            "requests": 100,
            "window": 60,
            "by": "ip",
            "exclude_paths": ["/ping", "/docs", "/redoc", "/openapi.json"],
        },
        "fields": [
            {
                "path": ["rate_limit", "enabled"],
                "group": "Limits",
                "default": True,
                "label": "Enabled",
                "type": "bool",
                "help": "Turn off to keep the settings without enforcing them.",
            },
            {
                "path": ["rate_limit", "requests"],
                "group": "Limits",
                "label": "Requests per window",
                "type": "number",
                "min": 1,
                "step": 1,
                "placeholder": "100",
            },
            {
                "path": ["rate_limit", "window"],
                "group": "Limits",
                "label": "Window (seconds)",
                "type": "number",
                "min": 1,
                "step": 1,
                "placeholder": "60",
            },
            {
                "path": ["rate_limit", "by"],
                "group": "Limits",
                "default": "ip",
                "label": "Limit by",
                "type": "select",
                "options": ["ip", "user", "global"],
                "help": "Count requests per client IP, per authenticated user, or all together.",
            },
            {
                "path": ["rate_limit", "backend"],
                "group": "Backend",
                "default": "memory",
                "label": "Backend",
                "type": "select",
                "options": ["memory", "redis", "custom"],
                "help": (
                    "memory counts per process. Use redis for multiple workers. custom "
                    "expects a BaseRateLimitBackend bound in InjectQ."
                ),
            },
            {
                "path": ["rate_limit", "redis", "url"],
                "group": "Backend",
                "label": "Redis URL",
                "type": "text",
                "placeholder": "${REDIS_URL}",
                "help": "Supports $VAR and ${VAR}. Not needed if Redis is bound in InjectQ.",
                "show_if": {"path": ["rate_limit", "backend"], "equals": "redis"},
            },
            {
                "path": ["rate_limit", "redis", "prefix"],
                "group": "Backend",
                "label": "Redis key prefix",
                "type": "text",
                "placeholder": "agentflow:rate-limit",
                "show_if": {"path": ["rate_limit", "backend"], "equals": "redis"},
            },
            {
                "path": ["rate_limit", "fail_open"],
                "group": "Backend",
                "default": True,
                "label": "Fail open",
                "type": "bool",
                "help": "Allow requests when the backend errors. Off means deny.",
            },
            {
                "path": ["rate_limit", "trusted_proxy_headers"],
                "group": "Proxy",
                "default": False,
                "label": "Trust X-Forwarded-For",
                "type": "bool",
                "help": "Only when the app sits behind a proxy you control.",
            },
            {
                "path": ["rate_limit", "trusted_proxy_hops"],
                "group": "Proxy",
                "label": "Trusted proxy hops",
                "type": "number",
                "min": 1,
                "step": 1,
                "placeholder": "1",
                "show_if": {"path": ["rate_limit", "trusted_proxy_headers"], "equals": True},
            },
            {
                "path": ["rate_limit", "trusted_proxies"],
                "group": "Proxy",
                "label": "Trusted proxy networks",
                "type": "list",
                "placeholder": "10.0.0.0/8",
                "help": (
                    "IPs or CIDR ranges your proxy connects from. X-Forwarded-For is ignored "
                    "for anyone else, so clients that reach the app directly cannot spoof it."
                ),
                "show_if": {"path": ["rate_limit", "trusted_proxy_headers"], "equals": True},
            },
            {
                "path": ["rate_limit", "exclude_paths"],
                "group": "Excluded paths",
                "label": "Excluded paths",
                "type": "list",
                "placeholder": "/ping",
            },
        ],
    },
    {
        "id": "websocket",
        "title": "WebSocket",
        "description": "Caps on concurrent realtime and streaming connections, per process.",
        "key": "websocket",
        "optional": True,
        "off_summary": "Concurrent WebSocket connections are not capped.",
        "default": {"max_connections": 1000, "max_connections_per_user": 10},
        "fields": [
            {
                "path": ["websocket", "max_connections"],
                "label": "Max connections",
                "type": "number",
                "min": 0,
                "step": 1,
                "placeholder": "1000",
                "help": "Per worker process. Defaults to 1000; 0 means unlimited.",
            },
            {
                "path": ["websocket", "max_connections_per_user"],
                "label": "Max connections per user",
                "type": "number",
                "min": 0,
                "step": 1,
                "placeholder": "10",
                "help": "Stops one account holding every slot. Defaults to 10; 0 means unlimited.",
            },
            {
                "path": ["websocket", "realtime_models"],
                "label": "Realtime models clients may pick",
                "type": "list",
                "placeholder": "gemini-2.5-flash-live",
                "help": (
                    "Models a /v1/graph/live client may request. Any other request uses the "
                    "agent's own model. Empty means clients cannot choose."
                ),
            },
        ],
    },
    {
        "id": "ag_ui",
        "title": "AG-UI",
        "description": "Serve the graph over the AG-UI protocol, for clients such as CopilotKit.",
        "key": "ag_ui",
        "optional": True,
        "off_summary": "The AG-UI endpoint (POST /v1/ag-ui) is not mounted.",
        "default": {"enabled": True},
        "fields": [
            {
                "path": ["ag_ui", "enabled"],
                "default": False,
                "label": "Enabled",
                "type": "bool",
                "help": "Mounts POST /v1/ag-ui. It uses the same auth as /v1/graph/stream.",
            },
        ],
        "notes": [
            'Needs the ag-ui extra: pip install "10xscale-agentflow-cli[ag-ui]".',
            "Browser tools reach the model only when they are also listed in remote_tools.",
        ],
    },
    {
        "id": "observability",
        "title": "Observability",
        "description": "Trace graph runs to Logfire and/or LangSmith.",
        "key": "observability",
        "optional": True,
        "off_summary": "Graph runs are not traced.",
        "default": {
            "level": "standard",
            "logfire": {"enabled": False},
            "langsmith": {"enabled": False},
        },
        "fields": [
            {
                "path": ["observability", "level"],
                "group": "Tracing",
                "default": "standard",
                "label": "Level",
                "type": "select",
                "options": ["spans", "standard", "full"],
                "help": "full records prompts and tool I/O and may contain PII.",
            },
            {
                "path": ["observability", "logfire", "enabled"],
                "group": "Logfire",
                "default": False,
                "label": "Logfire",
                "type": "bool",
            },
            {
                "path": ["observability", "logfire", "service_name"],
                "group": "Logfire",
                "label": "Logfire service name",
                "type": "text",
                "placeholder": "my-agent",
                "show_if": {"path": ["observability", "logfire", "enabled"], "equals": True},
            },
            {
                "path": ["observability", "logfire", "send_to_logfire"],
                "group": "Logfire",
                "default": True,
                "label": "Send to Logfire",
                "type": "bool",
                "show_if": {"path": ["observability", "logfire", "enabled"], "equals": True},
            },
            {
                "path": ["observability", "logfire", "console"],
                "group": "Logfire",
                "default": False,
                "label": "Print spans to console",
                "type": "bool",
                "show_if": {"path": ["observability", "logfire", "enabled"], "equals": True},
            },
            {
                "path": ["observability", "langsmith", "enabled"],
                "group": "LangSmith",
                "default": False,
                "label": "LangSmith",
                "type": "bool",
            },
            {
                "path": ["observability", "langsmith", "project"],
                "group": "LangSmith",
                "label": "LangSmith project",
                "type": "text",
                "placeholder": "my-agent",
                "show_if": {"path": ["observability", "langsmith", "enabled"], "equals": True},
            },
            {
                "path": ["observability", "langsmith", "endpoint"],
                "group": "LangSmith",
                "label": "LangSmith endpoint",
                "type": "text",
                "placeholder": "https://api.smith.langchain.com/otel",
                "show_if": {"path": ["observability", "langsmith", "enabled"], "equals": True},
            },
        ],
        "notes": ["Tokens stay in .env: LOGFIRE_TOKEN and LANGSMITH_API_KEY."],
    },
    {
        "id": "plugins",
        "title": "Plugins",
        "description": "Optional objects loaded by import path. Leave a field empty to skip it.",
        "key": None,
        "optional": False,
        "fields": [
            {
                "path": ["injectq"],
                "group": "Import paths",
                "label": "InjectQ container",
                "type": "text",
                "placeholder": "graph.dependencies:container",
            },
            {
                "path": ["store"],
                "group": "Import paths",
                "label": "Memory store",
                "type": "text",
                "placeholder": "graph.dependencies:store",
                "help": "A BaseStore instance for long-term memory.",
            },
            {
                "path": ["checkpointer"],
                "group": "Import paths",
                "label": "Checkpointer",
                "type": "text",
                "placeholder": "graph.dependencies:checkpointer",
                "help": (
                    "Not applied by the API server yet. Pass the checkpointer to "
                    "graph.compile() instead."
                ),
            },
            {
                "path": ["thread_name_generator"],
                "group": "Import paths",
                "label": "Thread name generator",
                "type": "text",
                "placeholder": "graph.thread_name_generator:MyNameGenerator",
            },
            {
                "path": ["redis"],
                "group": "Connections",
                "label": "Redis URL",
                "type": "text",
                "placeholder": "redis://localhost:6379/0",
                "help": (
                    "Shared cache for ownership checks. Used as-is: $VAR is not expanded "
                    "here, so leave it empty to fall back to REDIS_URL."
                ),
            },
        ],
    },
    {
        "id": "remote_tools",
        "title": "Remote tools",
        "description": "Tools the model can call that run in the client, not on the server.",
        "key": "remote_tools",
        "optional": True,
        "off_summary": "The model can only call tools that run on the server.",
        "default": [],
        "widget": "remote_tools",
        "fields": [],
    },
    {
        "id": "test",
        "title": "Testing",
        "description": "Defaults for agentflow test.",
        "key": "test",
        "optional": True,
        "off_summary": "agentflow test uses its built-in defaults.",
        "default": {"path": "tests", "coverage": False},
        "fields": [
            {"path": ["test", "path"], "label": "Tests path", "type": "text"},
            {"path": ["test", "coverage"], "label": "Coverage", "type": "bool", "default": False},
            {
                "path": ["test", "coverage_threshold"],
                "label": "Coverage threshold (%)",
                "type": "number",
                "min": 0,
                "step": 1,
                "placeholder": "80",
                "show_if": {"path": ["test", "coverage"], "equals": True},
            },
        ],
    },
    {
        "id": "evaluation",
        "title": "Evaluation",
        "description": "Defaults for agentflow eval.",
        "key": "evaluation",
        "optional": True,
        "off_summary": "agentflow eval uses its built-in defaults.",
        "default": {
            "directory": "evals",
            "output_dir": "eval_reports",
            "threshold": 0.75,
            "parallel": False,
            "max_concurrency": 4,
        },
        "fields": [
            {"path": ["evaluation", "directory"], "label": "Eval directory", "type": "text"},
            {"path": ["evaluation", "output_dir"], "label": "Report directory", "type": "text"},
            {
                "path": ["evaluation", "threshold"],
                "label": "Pass threshold",
                "type": "number",
                "min": 0,
                "step": 0.05,
                "help": "Between 0 and 1.",
            },
            {
                "path": ["evaluation", "parallel"],
                "label": "Run in parallel",
                "type": "bool",
                "default": False,
            },
            {
                "path": ["evaluation", "max_concurrency"],
                "label": "Max concurrency",
                "type": "number",
                "min": 1,
                "step": 1,
                "show_if": {"path": ["evaluation", "parallel"], "equals": True},
            },
        ],
    },
]


def build_schema() -> dict[str, Any]:
    """Return a fresh, JSON-serialisable copy of the editor schema."""
    return {"docs_url": DOCS_URL, "sections": copy.deepcopy(_SECTIONS)}


def section_for_key(key: str) -> str:
    """Map a top-level config key to the id of the section that renders it."""
    for section in _SECTIONS:
        if section["key"] == key:
            return section["id"]
        if section["key"] is None and any(f["path"][0] == key for f in section["fields"]):
            return section["id"]
    return "core"
