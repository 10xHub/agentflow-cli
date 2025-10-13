import types

import pytest

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.commands.version import VersionCommand
from agentflow_cli.cli.constants import CLI_VERSION
from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.exceptions import PyagenityCLIError


CLI_CUSTOM_EXIT = 5


class DummyOutput(OutputFormatter):
    def __init__(self):  # type: ignore[override]
        super().__init__()
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.infos: list[str] = []

    def error(self, msg: str):  # type: ignore[override]
        self.errors.append(msg)

    def success(self, msg: str):  # type: ignore[override]
        self.successes.append(msg)

    def info(self, msg: str):  # type: ignore[override]
        self.infos.append(msg)

    def print_banner(self, *args, **kwargs):  # type: ignore[override]
        pass


class ErrorCommand(BaseCommand):
    def execute(self, *args, **kwargs):  # pragma: no cover - not used directly
        return 0


def test_basecommand_handle_error_cli_error():
    out = DummyOutput()
    cmd = ErrorCommand(output=out)
    err = PyagenityCLIError("boom", exit_code=CLI_CUSTOM_EXIT)
    code = cmd.handle_error(err)
    assert code == CLI_CUSTOM_EXIT
    assert out.errors and "boom" in out.errors[0]


def test_basecommand_handle_error_generic():
    out = DummyOutput()
    cmd = ErrorCommand(output=out)
    err = RuntimeError("unexpected")
    code = cmd.handle_error(err)
    assert code == 1
    assert out.errors and "unexpected" in out.errors[0]


def test_version_command_error_branch(monkeypatch):
    out = DummyOutput()
    cmd = VersionCommand(output=out)  # type: ignore[arg-type]

    def boom(self):  # simulate failure in reading pyproject
        raise ValueError("cannot read")

    monkeypatch.setattr(VersionCommand, "_read_package_version", boom, raising=True)
    exit_code = cmd.execute()
    assert exit_code == 1
    assert not out.successes
    assert any("Unexpected" in e or "cannot read" in e for e in out.errors)


def test_version_command_success_path():
    out = DummyOutput()
    cmd = VersionCommand(output=out)  # type: ignore[arg-type]
    exit_code = cmd.execute()
    assert exit_code == 0
    assert any(CLI_VERSION in s for s in out.successes)
