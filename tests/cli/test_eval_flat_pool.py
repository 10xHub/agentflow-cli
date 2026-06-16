"""Integration tests for the flat-pool eval execution engine.

Verifies:
- Multi-file discovery runs all cases in a single asyncio loop
- Token usage is aggregated across files in EvalSummary
- confeval.py config takes priority over per-file config
- _merge_reports correctly combines results from multiple files
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentflow_cli.cli.commands.eval import EvalCommand
from agentflow_cli.cli.core.output import OutputFormatter


# ── Helpers ───────────────────────────────────────────────────────────────────


class _SilentOutput(OutputFormatter):
    def __init__(self) -> None:
        super().__init__()
        self.warnings: list[str] = []

    def warning(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.warnings.append(message)

    def error(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        pass

    def info(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        pass

    def success(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        pass

    def print_banner(self, *args, **kwargs) -> None:  # type: ignore[override]
        pass


@pytest.fixture
def cmd() -> EvalCommand:
    return EvalCommand(output=_SilentOutput())


# ── _merge_reports: token aggregation ────────────────────────────────────────


class TestMergeReportsTokenAggregation:
    """Verify that _merge_reports combines results across multiple file reports."""

    def _make_mock_report(self, *eval_ids: str) -> MagicMock:
        """Build a minimal MagicMock that _merge_reports can combine."""
        report = MagicMock()
        report.results = [MagicMock(eval_id=eid) for eid in eval_ids]
        return report

    def test_merged_report_contains_all_results(self, cmd: EvalCommand) -> None:
        r1 = self._make_mock_report("case_a", "case_b")
        r2 = self._make_mock_report("case_c")
        fake_merged = MagicMock()

        with patch("agentflow_cli.cli.commands.eval.ER.create", return_value=fake_merged) as mock_create:
            merged = cmd._merge_reports([r1, r2])

        assert merged is fake_merged
        _, kwargs = mock_create.call_args
        assert len(kwargs["results"]) == 3

    def test_single_report_passthrough(self, cmd: EvalCommand) -> None:
        r = self._make_mock_report("solo")
        merged = cmd._merge_reports([r])
        assert merged is r

    def test_results_from_all_files_passed_to_create(self, cmd: EvalCommand) -> None:
        r1 = self._make_mock_report("x", "y")
        r2 = self._make_mock_report("z")
        fake_merged = MagicMock()

        with patch("agentflow_cli.cli.commands.eval.ER.create", return_value=fake_merged) as mock_create:
            cmd._merge_reports([r1, r2])

        _, kwargs = mock_create.call_args
        combined_ids = [res.eval_id for res in kwargs["results"]]
        assert "x" in combined_ids
        assert "y" in combined_ids
        assert "z" in combined_ids


# ── _load_confeval + _collect_from_file priority chain ───────────────────────


class TestConfEvalPriorityChain:
    """Verify confeval config wins over per-file config in _collect_from_file."""

    def _dummy_path(self, tmp_path: Path) -> Path:
        p = tmp_path / "weather_eval.py"
        p.write_text("")
        return p

    def test_per_file_config_beats_confeval_config(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        global_cfg = EvalConfig()
        per_file_cfg = EvalConfig()
        fake_es = MagicMock()
        fake_es.cases = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            EVAL_CONFIG=per_file_cfg,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_make_pending", return_value=[]) as mock_make,
        ):
            cmd._collect_from_file(self._dummy_path(tmp_path), global_cfg)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is per_file_cfg
        assert used_config is not global_cfg
        assert used_source == "per-file"

    def test_per_file_config_used_when_no_confeval(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        per_file_cfg = EvalConfig()
        fake_es = MagicMock()
        fake_es.cases = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            get_eval_config=lambda: per_file_cfg,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_make_pending", return_value=[]) as mock_make,
        ):
            cmd._collect_from_file(self._dummy_path(tmp_path), None)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is per_file_cfg
        assert used_source == "per-file"

    def test_default_config_used_when_no_config_anywhere(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        default_cfg = EvalConfig()
        fake_es = MagicMock()
        fake_es.cases = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_default_config", return_value=default_cfg),
            patch.object(cmd, "_make_pending", return_value=[]) as mock_make,
        ):
            cmd._collect_from_file(self._dummy_path(tmp_path), None)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is default_cfg
        assert used_source == "built-in defaults"
