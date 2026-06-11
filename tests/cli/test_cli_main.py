from typer.testing import CliRunner
import pytest
from unittest.mock import MagicMock, patch
import agentflow_cli.cli.main as main_mod
from agentflow_cli.cli.exceptions import PyagenityCLIError

runner = CliRunner()


def test_play_command_delegates_to_api_command(monkeypatch):
    called = {}

    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)

    def fake_execute(self, **kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr(main_mod.APICommand, "execute", fake_execute)

    result = runner.invoke(main_mod.app, ["play", "--port", "9001", "--no-reload"])

    assert result.exit_code == 0
    assert called["config"] == "agentflow.json"
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 9001
    assert called["reload"] is False
    assert called["open_playground"] is True


def test_api_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.APICommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(main_mod.app, ["api", "-c", "custom.json", "-H", "1.2.3.4", "-p", "8080", "--no-reload", "--verbose"])
    assert result.exit_code == 0
    assert called["config"] == "custom.json"
    assert called["host"] == "1.2.3.4"
    assert called["port"] == 8080
    assert called["reload"] is False


def test_version_command(monkeypatch):
    called = []
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.VersionCommand,
        "execute",
        lambda self: called.append(True) or 0
    )
    result = runner.invoke(main_mod.app, ["version"])
    assert result.exit_code == 0
    assert len(called) == 1


def test_init_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.InitCommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(main_mod.app, ["init", "--path", "test_path", "--force"])
    assert result.exit_code == 0
    assert called["path"] == "test_path"
    assert called["force"] is True


def test_build_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.BuildCommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(
        main_mod.app,
        ["build", "-o", "Dfile", "--force", "--python-version", "3.12", "-p", "5000", "--docker-compose"]
    )
    assert result.exit_code == 0
    assert called["output_file"] == "Dfile"
    assert called["force"] is True
    assert called["python_version"] == "3.12"
    assert called["port"] == 5000
    assert called["docker_compose"] is True


def test_skills_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.SkillsCommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(
        main_mod.app,
        ["skills", "-a", "codex", "-p", "skills_path", "--force", "--all", "--list"]
    )
    assert result.exit_code == 0
    assert called["agent"] == "codex"
    assert called["path"] == "skills_path"
    assert called["force"] is True
    assert called["all_agents"] is True
    assert called["list_agents"] is True


def test_test_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.TestCommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(
        main_mod.app,
        ["test", "tests/foo.py", "--coverage", "--html", "-k", "foo_test", "--", "--lf", "-vv"]
    )
    assert result.exit_code == 0
    assert called["path"] == "tests/foo.py"
    assert called["coverage"] is True
    assert called["html"] is True
    assert called["keyword"] == "foo_test"
    assert called["extra_args"] == ("--lf", "-vv")


def test_eval_command(monkeypatch):
    called = {}
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.EvalCommand,
        "execute",
        lambda self, **kwargs: called.update(kwargs) or 0
    )
    result = runner.invoke(
        main_mod.app,
        ["eval", "target_eval", "-o", "out_dir", "--no-report", "-t", "0.8", "--open", "--parallel", "-c", "8"]
    )
    assert result.exit_code == 0
    assert called["target"] == "target_eval"
    assert called["output_dir"] == "out_dir"
    assert called["no_report"] is True
    assert called["threshold"] == 0.8
    assert called["open_report"] is True
    assert called["parallel"] is True
    assert called["max_concurrency"] == 8


def test_a2a_command_is_not_exposed():
    result = runner.invoke(main_mod.app, ["a2a"])

    assert result.exit_code != 0
    assert "No such command 'a2a'" in result.output


def test_handle_pyagenity_cli_error(monkeypatch):
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.VersionCommand,
        "execute",
        lambda self: (_ for _ in ()).throw(PyagenityCLIError("Custom error message", exit_code=42))
    )
    result = runner.invoke(main_mod.app, ["version"])
    assert result.exit_code == 42


def test_handle_generic_exception(monkeypatch):
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        main_mod.VersionCommand,
        "execute",
        lambda self: (_ for _ in ()).throw(ValueError("Some generic value error"))
    )
    result = runner.invoke(main_mod.app, ["version"])
    assert result.exit_code == 1


def test_main_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    with patch("agentflow_cli.cli.main.app", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as exc_info:
            main_mod.main()
        assert exc_info.value.code == 130


def test_main_generic_exception(monkeypatch):
    monkeypatch.setattr(main_mod, "setup_cli_logging", lambda **kwargs: None)
    with patch("agentflow_cli.cli.main.app", side_effect=ValueError("Main error")):
        with pytest.raises(SystemExit) as exc_info:
            main_mod.main()
        assert exc_info.value.code == 1

