import io
import os
from pathlib import Path

import pytest

import tenxgraph_api.cli.commands.api as api_mod
from tenxgraph_api.cli.commands.api import APICommand
from tenxgraph_api.cli.core import validation as validation_module
from tenxgraph_api.cli.core.output import OutputFormatter


@pytest.fixture
def silent_output():
    """A real formatter with output suppressed, so it tracks the live surface."""
    return OutputFormatter(stream=io.StringIO(), quiet=True)


def test_api_command_with_env_file(monkeypatch, tmp_path, silent_output):
    # Prepare a fake config file and .env
    cfg = tmp_path / "10xgraph.json"
    # Provide minimal valid configuration expected by current validation (top-level 'agent')
    cfg.write_text('{"agent": "graph/react.py"}', encoding="utf-8")
    env_file = tmp_path / ".env.dev"
    env_file.write_text("FOO=BAR\n", encoding="utf-8")

    # Stub ConfigManager to return our paths
    class DummyCfg:
        def __init__(self, path):
            self._path = Path(path)

        def find_config_file(self, _):
            return self._path

        def load_config(self, _):
            return {}

        def resolve_env_file(self):
            return env_file

    # Patch the ConfigManager reference used inside api module
    monkeypatch.setattr(api_mod, "ConfigManager", lambda: DummyCfg(cfg))

    # Stub validator
    def fake_validate_cli_options(host, port, config):
        return {"host": host, "port": port, "config": config}

    monkeypatch.setattr(validation_module, "validate_cli_options", fake_validate_cli_options)

    # Prevent actual uvicorn run

    def fake_run(*_, **__):
        return None

    monkeypatch.setattr(api_mod.uvicorn, "run", fake_run)

    cmd = APICommand(output=silent_output)
    code = cmd.execute(config=str(cfg), reload=False)
    assert code == 0
    # Ensure env variable loaded
    assert os.environ.get("FOO") == "BAR"
