"""Root runtime, startup isolation, and new command contract tests."""

from __future__ import annotations

from typer.testing import CliRunner

import agentflow_cli.cli.main as main_mod
from agentflow_cli.cli.user_config import UserConfigStore


runner = CliRunner()


def test_root_help_does_not_import_command_implementations(monkeypatch) -> None:
    imported: list[str] = []
    original = main_mod.importlib.import_module

    def recording_import(name: str, *args, **kwargs):
        if name.startswith("agentflow_cli.cli.commands."):
            imported.append(name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(main_mod.importlib, "import_module", recording_import)
    result = runner.invoke(main_mod.app, ["--help"])
    assert result.exit_code == 0
    assert imported == []
    assert "dev" in result.output
    assert "audit" in result.output


def test_root_version_is_script_friendly() -> None:
    result = runner.invoke(main_mod.app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == main_mod.CLI_VERSION


def test_plain_and_no_color_global_options() -> None:
    result = runner.invoke(main_mod.app, ["--format", "plain", "--color", "never", "version"])
    assert result.exit_code == 0
    assert "\x1b[" not in result.output
    assert "Version" in result.output


def test_no_animation_alias_selects_static_output() -> None:
    result = runner.invoke(main_mod.app, ["--no-animation", "audit"])
    assert result.exit_code == 0
    assert "Audit" in result.output


def test_dev_delegates_to_api_with_open_policy(monkeypatch) -> None:
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.APICommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0,
    )
    result = runner.invoke(main_mod.app, ["dev", "--no-open", "--port", "8123"])
    assert result.exit_code == 0
    assert called["open_playground"] is False
    assert called["port"] == 8123


def test_lazy_dependency_error_has_recovery_code(monkeypatch) -> None:
    original = main_mod.importlib.import_module

    def fail_eval(name: str, *args, **kwargs):
        if name == "agentflow_cli.cli.commands.eval":
            raise ImportError("missing evaluation symbol")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(main_mod.importlib, "import_module", fail_eval)
    result = runner.invoke(main_mod.app, ["eval"])
    assert result.exit_code == 4
    assert "AF-DEPS-001" in result.output
    assert "agentflow audit" in result.output


def test_config_commands_round_trip(monkeypatch, tmp_path) -> None:
    store = UserConfigStore(tmp_path / "config.json")
    monkeypatch.setattr(main_mod, "UserConfigStore", lambda: store)

    set_result = runner.invoke(main_mod.app, ["config", "set", "output.format", "plain"])
    assert set_result.exit_code == 0
    assert store.get("output.format") == "plain"

    get_result = runner.invoke(main_mod.app, ["config", "get", "output.format"])
    assert get_result.exit_code == 0
    assert get_result.output.strip() == "plain"

    list_result = runner.invoke(main_mod.app, ["config", "list"])
    assert list_result.exit_code == 0
    assert "output.format" in list_result.output

    validate_result = runner.invoke(main_mod.app, ["config", "validate"])
    assert validate_result.exit_code == 0

    unset_result = runner.invoke(main_mod.app, ["config", "unset", "output.format"])
    assert unset_result.exit_code == 0
    assert store.get("output.format") is None
