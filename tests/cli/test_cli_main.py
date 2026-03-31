from typer.testing import CliRunner

import agentflow_cli.cli.main as main_mod


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


def test_a2a_command_is_not_exposed():
    result = runner.invoke(main_mod.app, ["a2a"])

    assert result.exit_code != 0
    assert "No such command 'a2a'" in result.output
