"""The AG-UI endpoint is off unless agentflow.json turns it on."""

# ruff: noqa: S101

import json
from pathlib import Path

import pytest
from fastapi import FastAPI

from agentflow_cli.src.app.core.auth.route_guard import _iter_routes, find_unprotected_routes
from agentflow_cli.src.app.core.config.graph_config import AgUiConfig, GraphConfig
from agentflow_cli.src.app.routers import setup_router
from agentflow_cli.src.app.routers.setup_router import init_routes


def _config(tmp_path: Path, data: dict) -> GraphConfig:
    path = tmp_path / "agentflow.json"
    path.write_text(json.dumps({"agent": "mod:app", **data}))
    return GraphConfig(str(path))


def _paths(app: FastAPI) -> set[str]:
    return {path for path, _route, _guarded in _iter_routes(app.routes)}


def test_ag_ui_is_disabled_when_key_is_missing(tmp_path: Path):
    assert _config(tmp_path, {}).ag_ui.enabled is False


def test_ag_ui_is_disabled_by_default_in_the_object(tmp_path: Path):
    assert _config(tmp_path, {"ag_ui": {}}).ag_ui.enabled is False


def test_ag_ui_can_be_enabled(tmp_path: Path):
    assert _config(tmp_path, {"ag_ui": {"enabled": True}}).ag_ui.enabled is True


def test_ag_ui_rejects_a_non_object():
    with pytest.raises(ValueError, match="ag_ui must be an object"):
        AgUiConfig.from_dict(True)  # type: ignore[arg-type]


def test_ag_ui_rejects_a_non_boolean_flag():
    with pytest.raises(ValueError, match=r"ag_ui\.enabled must be a boolean"):
        AgUiConfig.from_dict({"enabled": "sometimes"})


def test_route_is_not_mounted_by_default():
    app = FastAPI()
    init_routes(app)
    assert "/v1/ag-ui" not in _paths(app)


def test_route_is_mounted_when_enabled():
    app = FastAPI()
    init_routes(app, ag_ui=True)
    assert "/v1/ag-ui" in _paths(app)


def test_enabled_route_is_guarded():
    app = FastAPI()
    init_routes(app, ag_ui=True)
    assert not any("/v1/ag-ui" in route for route in find_unprotected_routes(app))


def test_missing_sdk_fails_with_install_hint(monkeypatch):
    def _missing():
        raise ModuleNotFoundError("No module named 'ag_ui'", name="ag_ui")

    monkeypatch.setattr(setup_router, "_import_ag_ui_router", _missing)
    with pytest.raises(RuntimeError, match=r"10xscale-agentflow-cli\[ag-ui\]"):
        init_routes(FastAPI(), ag_ui=True)


def test_client_tools_are_allowed_by_default(tmp_path: Path):
    assert _config(tmp_path, {"ag_ui": {"enabled": True}}).ag_ui.allow_client_tools is True


def test_client_tools_can_be_disallowed(tmp_path: Path):
    config = _config(tmp_path, {"ag_ui": {"enabled": True, "allow_client_tools": False}})
    assert config.ag_ui.allow_client_tools is False


def test_client_tools_flag_must_be_boolean():
    with pytest.raises(ValueError, match=r"ag_ui\.allow_client_tools must be a boolean"):
        AgUiConfig.from_dict({"allow_client_tools": "sometimes"})
