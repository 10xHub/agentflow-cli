"""Tests for the eval CLI command."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from agentflow_cli.cli.commands.eval import EvalCommand
from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.exceptions import EvaluationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyOutput(OutputFormatter):
    """Capture output instead of printing to terminal."""

    def __init__(self):  # type: ignore[override]
        super().__init__()
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str, **kw) -> None:  # type: ignore[override]
        self.errors.append(msg)

    def success(self, msg: str, **kw) -> None:  # type: ignore[override]
        self.successes.append(msg)

    def info(self, msg: str, **kw) -> None:  # type: ignore[override]
        self.infos.append(msg)

    def warning(self, msg: str, **kw) -> None:  # type: ignore[override]
        self.warnings.append(msg)

    def print_banner(self, *args, **kwargs) -> None:  # type: ignore[override]
        pass


def _make_fake_report():
    """Build a minimal mock EvalReport with the fields EvalCommand uses."""
    summary = MagicMock()
    summary.passed_cases = 3
    summary.total_cases = 4
    summary.pass_rate = 0.75

    report = MagicMock()
    report.summary = summary
    report.model_dump.return_value = {
        "eval_set_id": "test_set",
        "results": [],
        "summary": {
            "total_cases": 4,
            "passed_cases": 3,
            "pass_rate": 0.75,
        },
    }
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEvalCommandValidation:
    """Input validation tests (no evaluation is actually run)."""

    def test_eval_file_not_found(self):
        out = DummyOutput()
        cmd = EvalCommand(output=out)
        code = cmd.execute(
            agent_module="graph.react",
            eval_file="/nonexistent/eval.json",
        )
        assert code == 1
        assert any("not found" in e for e in out.errors)

    def test_config_file_not_found(self, tmp_path):
        """Config file specified but does not exist."""
        # Create a dummy eval file so we pass the first check
        eval_file = tmp_path / "test.evalset.json"
        eval_file.write_text("{}")

        out = DummyOutput()
        cmd = EvalCommand(output=out)
        code = cmd.execute(
            agent_module="graph.react",
            eval_file=str(eval_file),
            config_file="/nonexistent/config.json",
        )
        assert code == 1
        assert any("not found" in e for e in out.errors)


class TestEvalCommandExecution:
    """Verify the command wires to AgentEvaluator and writes JSON."""

    @patch("agentflow_cli.cli.commands.eval.EvalCommand._run_evaluation", new_callable=AsyncMock)
    def test_successful_run(self, mock_run, tmp_path):
        fake_report = _make_fake_report()
        mock_run.return_value = fake_report

        eval_file = tmp_path / "test.evalset.json"
        eval_file.write_text("{}")

        output_file = tmp_path / "result.json"

        out = DummyOutput()
        cmd = EvalCommand(output=out)
        code = cmd.execute(
            agent_module="graph.react",
            eval_file=str(eval_file),
            output=str(output_file),
        )

        assert code == 0
        assert output_file.exists()
        assert any("complete" in s.lower() for s in out.successes)

        # Verify the JSON content is valid
        data = json.loads(output_file.read_text())
        assert data["eval_set_id"] == "test_set"

    @patch("agentflow_cli.cli.commands.eval.EvalCommand._run_evaluation", new_callable=AsyncMock)
    def test_default_output_filename(self, mock_run, tmp_path, monkeypatch):
        """When --output is not given, filename includes a timestamp."""
        fake_report = _make_fake_report()
        mock_run.return_value = fake_report

        eval_file = tmp_path / "test.evalset.json"
        eval_file.write_text("{}")

        # Run from tmp_path so the default output lands there
        monkeypatch.chdir(tmp_path)

        out = DummyOutput()
        cmd = EvalCommand(output=out)
        code = cmd.execute(
            agent_module="graph.react",
            eval_file=str(eval_file),
        )

        assert code == 0
        # Check a file matching eval_report_*.json was created
        json_files = list(tmp_path.glob("eval_report_*.json"))
        assert len(json_files) == 1

    @patch("agentflow_cli.cli.commands.eval.EvalCommand._run_evaluation", new_callable=AsyncMock)
    def test_evaluation_failure_returns_error_code(self, mock_run, tmp_path):
        mock_run.side_effect = RuntimeError("LLM API key missing")

        eval_file = tmp_path / "test.evalset.json"
        eval_file.write_text("{}")

        out = DummyOutput()
        cmd = EvalCommand(output=out)
        code = cmd.execute(
            agent_module="graph.react",
            eval_file=str(eval_file),
        )

        assert code == 1
        assert any("failed" in e.lower() for e in out.errors)


class TestEvaluationError:
    """EvaluationError exception behaviour."""

    def test_attributes_stored(self):
        err = EvaluationError(
            "boom",
            agent_module="graph.react",
            eval_file="test.json",
        )
        assert err.message == "boom"
        assert err.agent_module == "graph.react"
        assert err.eval_file == "test.json"
        assert err.exit_code == 1
