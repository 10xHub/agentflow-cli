import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import NoMatchFound

from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.core.config.setup_middleware import setup_middleware
from agentflow_cli.src.app.routers.setup_router import init_routes


HTTP_NOT_FOUND = 404
HTTP_OK = 200


def test_init_routes_includes_ping_only():
    app = FastAPI()
    setup_middleware(app)
    init_routes(app)
    client = TestClient(app)

    r = client.get("/ping")
    assert r.status_code == HTTP_OK
    assert r.json()["data"] == "pong"

    # Graph and checkpointer routers are present but actual endpoints may be complex.
    # Just verify that non-existent path returns 404 to execute include_router lines.
    r2 = client.get("/non-existent")
    assert r2.status_code == HTTP_NOT_FOUND


class _StubWebSocketConfig:
    def __init__(self, enabled: bool, declared: bool = True):
        self.enabled = enabled
        self.enabled_declared = declared
        self.max_connections = None


class _StubRouterConfig:
    def __init__(self, disabled: set[str], declared: set[str] | None = None):
        self.disabled = frozenset(disabled)
        self.declared = frozenset(disabled if declared is None else declared)

    def is_enabled(self, name: str) -> bool:
        return name not in self.disabled


class _StubGraphConfig:
    """Stand-in for the two blocks init_routes reads: ``websocket`` and ``routers``."""

    def __init__(self, ws_enabled: bool = True, disabled: set[str] | None = None):
        self.websocket = _StubWebSocketConfig(ws_enabled)
        self.routers = _StubRouterConfig(disabled or set())


def _route_path(app: FastAPI, name: str, **path_params: str) -> str | None:
    """Path of the route registered under ``name``, or None when it is not mounted.

    ``url_path_for`` also raises NoMatchFound when a path parameter is missing, so a
    parameterised route must be asked for with its parameters or it looks unmounted.
    """
    try:
        return str(app.url_path_for(name, **path_params))
    except NoMatchFound:
        return None


def test_graph_ws_registered_when_config_absent():
    app = FastAPI()
    init_routes(app)

    assert _route_path(app, "websocket_graph") == "/v1/graph/ws"


def test_graph_ws_registered_when_enabled():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(ws_enabled=True))

    assert _route_path(app, "websocket_graph") == "/v1/graph/ws"


def test_graph_ws_omitted_when_disabled():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(ws_enabled=False))

    assert _route_path(app, "websocket_graph") is None
    # Only the streaming endpoint is gated; the realtime bridge stays mounted.
    assert _route_path(app, "realtime_graph_ws") == "/v1/graph/live"


def test_rest_routes_unaffected_when_ws_disabled():
    app = FastAPI()
    setup_middleware(app)
    init_routes(app, graph_config=_StubGraphConfig(ws_enabled=False))
    client = TestClient(app)

    assert client.get("/ping").status_code == HTTP_OK


def test_optional_routers_mounted_by_default():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(disabled=set()))

    assert _route_path(app, "upload_file") == "/v1/files/upload"
    assert _route_path(app, "list_eval_runs") == "/v1/evals/runs"


def test_disabling_media_removes_only_media_routes():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(disabled={"media"}))

    assert _route_path(app, "upload_file") is None
    assert _route_path(app, "get_multimodal_config") is None
    # Neighbouring routers are untouched.
    assert _route_path(app, "list_eval_runs") == "/v1/evals/runs"
    assert _route_path(app, "list_threads") == "/v1/threads"


def test_disabling_checkpointer_and_store():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(disabled={"checkpointer", "store"}))

    assert _route_path(app, "list_threads") is None
    assert _route_path(app, "create_memory") is None
    assert _route_path(app, "upload_file") == "/v1/files/upload"


def test_graph_and_ping_stay_mounted_when_disabled():
    app = FastAPI()
    init_routes(app, graph_config=_StubGraphConfig(disabled={"graph", "ping"}))

    assert _route_path(app, "ping_server") == "/ping"
    assert _route_path(app, "websocket_graph") == "/v1/graph/ws"


def test_config_warnings_are_logged_once_per_startup(tmp_path, caplog):
    """The routers block is parsed once, not once per router in the include loop."""
    cfg_path = tmp_path / "agentflow.json"
    cfg_path.write_text(json.dumps({"agent": "mod:app", "routers": {"eval": False}}))
    config = GraphConfig(str(cfg_path))

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(app, config)

    assert caplog.text.count("Unknown router 'eval'") == 1


class _StubWebSocketOnlyConfig:
    """Config where both websocket spellings are written, and can be set independently."""

    def __init__(self, *, block_enabled: bool, routers_enabled: bool):
        self.websocket = _StubWebSocketConfig(block_enabled)
        self.routers = _StubRouterConfig(
            set() if routers_enabled else {"websocket"}, declared={"websocket"}
        )


def test_websocket_mounted_when_both_spellings_enabled():
    app = FastAPI()
    init_routes(
        app,
        graph_config=_StubWebSocketOnlyConfig(block_enabled=True, routers_enabled=True),
    )

    assert _route_path(app, "websocket_graph") == "/v1/graph/ws"


def test_routers_websocket_false_unmounts_it():
    app = FastAPI()
    init_routes(
        app,
        graph_config=_StubWebSocketOnlyConfig(block_enabled=True, routers_enabled=False),
    )

    assert _route_path(app, "websocket_graph") is None


def test_websocket_block_disabled_unmounts_it():
    app = FastAPI()
    init_routes(
        app,
        graph_config=_StubWebSocketOnlyConfig(block_enabled=False, routers_enabled=True),
    )

    assert _route_path(app, "websocket_graph") is None


def test_both_spellings_false_unmounts_it_once():
    app = FastAPI()
    init_routes(
        app,
        graph_config=_StubWebSocketOnlyConfig(block_enabled=False, routers_enabled=False),
    )

    assert _route_path(app, "websocket_graph") is None


def test_disagreeing_spellings_warn_naming_both_keys(caplog):
    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(
            app,
            graph_config=_StubWebSocketOnlyConfig(block_enabled=True, routers_enabled=False),
        )

    assert "websocket.enabled" in caplog.text
    assert "routers.websocket" in caplog.text


def test_agreeing_spellings_do_not_warn(caplog):
    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(
            app,
            graph_config=_StubWebSocketOnlyConfig(block_enabled=False, routers_enabled=False),
        )

    assert "disagree" not in caplog.text


def test_real_config_with_both_spellings(tmp_path):
    """A config that sets both keys parses and mounts nothing extra."""
    cfg_path = tmp_path / "agentflow.json"
    cfg_path.write_text(
        json.dumps(
            {
                "agent": "mod:app",
                "routers": {"websocket": False, "evals": False},
                "websocket": {"enabled": False, "max_connections": 10},
            }
        )
    )

    app = FastAPI()
    init_routes(app, GraphConfig(str(cfg_path)))

    assert _route_path(app, "websocket_graph") is None
    assert _route_path(app, "list_eval_runs") is None
    assert _route_path(app, "list_threads") == "/v1/threads"


def _config_from(tmp_path, data: dict) -> GraphConfig:
    cfg_path = tmp_path / "agentflow.json"
    cfg_path.write_text(json.dumps({"agent": "mod:app", **data}))
    return GraphConfig(str(cfg_path))


def test_only_routers_websocket_set_does_not_warn(tmp_path, caplog):
    """A key left unwritten must not count as disagreeing with the one you did write."""
    config = _config_from(tmp_path, {"routers": {"websocket": False}})

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(app, config)

    assert _route_path(app, "websocket_graph") is None
    assert "disagree" not in caplog.text


def test_only_websocket_block_set_does_not_warn(tmp_path, caplog):
    config = _config_from(tmp_path, {"websocket": {"enabled": False}})

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(app, config)

    assert _route_path(app, "websocket_graph") is None
    assert "disagree" not in caplog.text


def test_both_keys_set_and_agreeing_does_not_warn(tmp_path, caplog):
    config = _config_from(
        tmp_path, {"routers": {"websocket": False}, "websocket": {"enabled": False}}
    )

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(app, config)

    assert "disagree" not in caplog.text


def test_both_keys_set_and_conflicting_warns(tmp_path, caplog):
    config = _config_from(
        tmp_path, {"routers": {"websocket": False}, "websocket": {"enabled": True}}
    )

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="agentflow_api"):
        init_routes(app, config)

    assert _route_path(app, "websocket_graph") is None
    assert "disagree" in caplog.text
