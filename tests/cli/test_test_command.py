"""Unit tests for TestCommand."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from agentflow_cli.cli.commands.test import TestCommand
from agentflow_cli.cli.core.output import OutputFormatter

# Disable pytest collection for the imported TestCommand class
TestCommand.__test__ = False


class _SilentOutput(OutputFormatter):
    def __init__(self) -> None:
        super().__init__()
        self.successes = []
        self.errors = []
        self.infos = []

    def success(self, message: str, emoji: bool = True) -> None:
        self.successes.append(message)

    def error(self, message: str, emoji: bool = True) -> None:
        self.errors.append(message)

    def info(self, message: str, emoji: bool = True) -> None:
        self.infos.append(message)

    def print_banner(self, *args, **kwargs) -> None:
        pass


@pytest.fixture
def cmd() -> TestCommand:
    return TestCommand(output=_SilentOutput())


def test_execute_simple_success(cmd):
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0

    with patch("subprocess.run", return_value=mock_run_res) as mock_run, \
         patch("agentflow_cli.cli.commands.test.ConfigManager.auto_discover_config", return_value=None):
         
        code = cmd.execute(path="tests/unit_tests")
        assert code == 0
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "pytest" in args
        assert "tests/unit_tests" in args


def test_execute_failure(cmd):
    mock_run_res = MagicMock()
    mock_run_res.returncode = 1

    with patch("subprocess.run", return_value=mock_run_res) as mock_run, \
         patch("agentflow_cli.cli.commands.test.ConfigManager.auto_discover_config", return_value=None):
         
        code = cmd.execute()
        assert code == 1
        assert len(cmd.output.errors) > 0


def test_execute_with_config_overrides(cmd):
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0

    # Mock ConfigManager to return test config
    mock_cm = MagicMock()
    mock_cm.auto_discover_config.return_value = "agentflow.json"
    mock_cm.get_test_config.return_value = {
        "path": "custom_tests",
        "coverage": True,
        "coverage_threshold": 90,
    }

    with patch("subprocess.run", return_value=mock_run_res) as mock_run, \
         patch("agentflow_cli.cli.commands.test.ConfigManager", return_value=mock_cm), \
         patch("webbrowser.open") as mock_web_open:
         
        code = cmd.execute(coverage=False, html=True)  # html=True requires coverage config override
        assert code == 0
        args = mock_run.call_args[0][0]
        assert "custom_tests" in args
        assert "--cov=." in args
        assert "--cov-fail-under=90" in args
        mock_web_open.assert_called_once()


def test_execute_quiet_and_extra_args(cmd):
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0

    with patch("subprocess.run", return_value=mock_run_res) as mock_run, \
         patch("agentflow_cli.cli.commands.test.ConfigManager.auto_discover_config", return_value=None):
         
        cmd.execute(quiet=True, keyword="my_test", extra_args=("-x", "--lf"))
        args = mock_run.call_args[0][0]
        assert "-q" in args
        assert "-k" in args
        assert "my_test" in args
        assert "-x" in args
        assert "--lf" in args
