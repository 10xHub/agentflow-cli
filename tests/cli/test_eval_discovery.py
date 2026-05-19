"""Unit tests for EvalCommand discovery and module introspection."""

from __future__ import annotations

import asyncio
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentflow_cli.cli.commands.eval import EvalCommand
from agentflow_cli.cli.core.output import OutputFormatter


# ── Silent test output ────────────────────────────────────────────────────────


class _SilentOutput(OutputFormatter):
    """OutputFormatter that records messages without printing."""

    def __init__(self) -> None:
        super().__init__()
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def warning(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.warnings.append(message)

    def error(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.errors.append(message)

    def info(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        pass

    def success(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        pass

    def print_banner(self, *args, **kwargs) -> None:  # type: ignore[override]
        pass


@pytest.fixture
def cmd() -> EvalCommand:
    return EvalCommand(output=_SilentOutput())


# ── _discover ─────────────────────────────────────────────────────────────────


class TestDiscover:
    def test_single_file_returned_directly(self, tmp_path: Path, cmd: EvalCommand) -> None:
        f = tmp_path / "foo_eval.py"
        f.write_text("")
        assert cmd._discover(f) == [f]

    def test_finds_star_eval_pattern(self, tmp_path: Path, cmd: EvalCommand) -> None:
        a = tmp_path / "weather_eval.py"
        a.write_text("")
        # "helpers.py" matches neither *_eval.py nor eval_*.py
        (tmp_path / "helpers.py").write_text("")
        found = cmd._discover(tmp_path)
        assert a in found
        assert (tmp_path / "helpers.py") not in found

    def test_finds_eval_star_pattern(self, tmp_path: Path, cmd: EvalCommand) -> None:
        a = tmp_path / "eval_weather.py"
        a.write_text("")
        found = cmd._discover(tmp_path)
        assert a in found

    def test_deduplication(self, tmp_path: Path, cmd: EvalCommand) -> None:
        # A file matching both patterns must appear only once.
        f = tmp_path / "eval_weather_eval.py"
        f.write_text("")
        found = cmd._discover(tmp_path)
        assert found.count(f) == 1

    def test_recursive_discovery(self, tmp_path: Path, cmd: EvalCommand) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        a = sub / "agent_eval.py"
        a.write_text("")
        assert a in cmd._discover(tmp_path)

    def test_empty_directory_returns_empty(self, tmp_path: Path, cmd: EvalCommand) -> None:
        assert cmd._discover(tmp_path) == []

    def test_non_eval_files_ignored(self, tmp_path: Path, cmd: EvalCommand) -> None:
        (tmp_path / "helpers.py").write_text("")
        (tmp_path / "conftest.py").write_text("")
        assert cmd._discover(tmp_path) == []


# ── _run_file_sync ────────────────────────────────────────────────────────────


class TestRunFileSync:
    """Test the module introspection priority: run() → get_eval_set() → skip."""

    def _dummy_path(self, tmp_path: Path) -> Path:
        p = tmp_path / "x_eval.py"
        p.write_text("")
        return p

    def test_run_function_sync_called(self, tmp_path: Path, cmd: EvalCommand) -> None:
        sentinel = MagicMock()
        fake_mod = types.SimpleNamespace(run=lambda: sentinel)
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))
        assert result is sentinel

    def test_run_function_async_awaited(self, tmp_path: Path, cmd: EvalCommand) -> None:
        sentinel = MagicMock()

        async def _async_run() -> object:
            return sentinel

        fake_mod = types.SimpleNamespace(run=_async_run)
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))
        assert result is sentinel

    def test_get_eval_set_with_get_eval_config(self, tmp_path: Path, cmd: EvalCommand) -> None:
        fake_eval_set = MagicMock()
        fake_config = MagicMock()
        fake_report = MagicMock()
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_eval_set,
            get_eval_config=lambda: fake_config,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_run_with_evaluator", return_value=fake_report) as mock_run,
        ):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))

        mock_run.assert_called_once_with(fake_mod, fake_eval_set, fake_config)
        assert result is fake_report

    def test_get_eval_set_with_eval_config_constant(self, tmp_path: Path, cmd: EvalCommand) -> None:
        fake_eval_set = MagicMock()
        fake_config = MagicMock()
        fake_report = MagicMock()
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_eval_set,
            EVAL_CONFIG=fake_config,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_run_with_evaluator", return_value=fake_report) as mock_run,
        ):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))

        mock_run.assert_called_once_with(fake_mod, fake_eval_set, fake_config)
        assert result is fake_report

    def test_get_eval_set_uses_default_config_when_none_provided(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        fake_eval_set = MagicMock()
        fake_report = MagicMock()
        # Module has get_eval_set but neither get_eval_config nor EVAL_CONFIG
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_eval_set,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_run_with_evaluator", return_value=fake_report) as mock_run,
        ):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))

        assert mock_run.called
        assert result is fake_report

    def test_run_takes_priority_over_get_eval_set(self, tmp_path: Path, cmd: EvalCommand) -> None:
        """run() must be called even when get_eval_set also exists."""
        run_result = MagicMock(name="run_result")
        eval_set_result = MagicMock(name="eval_set_result")
        fake_mod = types.SimpleNamespace(
            run=lambda: run_result,
            get_eval_set=lambda: eval_set_result,
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_run_with_evaluator") as mock_run_with,
        ):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))

        assert result is run_result
        mock_run_with.assert_not_called()

    def test_no_entry_point_returns_none_and_warns(self, tmp_path: Path, cmd: EvalCommand) -> None:
        fake_mod = types.SimpleNamespace()  # no run(), no get_eval_set()
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._run_file_sync(self._dummy_path(tmp_path))

        assert result is None
        assert any(
            "skip" in w.lower() or "no run" in w.lower() or "get_eval_set" in w.lower()
            for w in cmd.output.warnings  # type: ignore[attr-defined]
        )


# ── _merge_reports ────────────────────────────────────────────────────────────


class TestMergeReports:
    def test_single_report_returned_as_is(self, cmd: EvalCommand) -> None:
        r = MagicMock()
        assert cmd._merge_reports([r]) is r

    def test_multiple_reports_combined(self, cmd: EvalCommand) -> None:
        r1 = MagicMock()
        r1.results = [MagicMock(), MagicMock()]
        r2 = MagicMock()
        r2.results = [MagicMock()]

        fake_merged = MagicMock()
        with patch(
            "agentflow_cli.cli.commands.eval.ER.create", return_value=fake_merged
        ) as mock_create:
            result = cmd._merge_reports([r1, r2])

        assert result is fake_merged
        _, kwargs = mock_create.call_args
        assert len(kwargs["results"]) == 3  # 2 from r1 + 1 from r2
