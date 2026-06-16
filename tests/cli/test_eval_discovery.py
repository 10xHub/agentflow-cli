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


# ── _load_confeval ────────────────────────────────────────────────────────────


class TestLoadConfeval:
    """Test confeval.py loading with priority: get_eval_config() > EVAL_CONFIG > None."""

    def test_no_confeval_returns_none(self, tmp_path: Path, cmd: EvalCommand) -> None:
        result = cmd._load_confeval(tmp_path)
        assert result is None

    def test_get_eval_config_called_when_present(self, tmp_path: Path, cmd: EvalCommand) -> None:
        from agentflow.qa.evaluation import EvalConfig

        expected = EvalConfig()
        fake_mod = types.SimpleNamespace(get_eval_config=lambda: expected)
        confeval = tmp_path / "confeval.py"
        confeval.write_text("")
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._load_confeval(tmp_path)
        assert result is expected

    def test_eval_config_constant_used_as_fallback(self, tmp_path: Path, cmd: EvalCommand) -> None:
        from agentflow.qa.evaluation import EvalConfig

        expected = EvalConfig()
        fake_mod = types.SimpleNamespace(EVAL_CONFIG=expected)
        confeval = tmp_path / "confeval.py"
        confeval.write_text("")
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._load_confeval(tmp_path)
        assert result is expected

    def test_get_eval_config_takes_priority_over_constant(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        via_fn = EvalConfig()
        via_const = EvalConfig()
        fake_mod = types.SimpleNamespace(
            get_eval_config=lambda: via_fn, EVAL_CONFIG=via_const
        )
        confeval = tmp_path / "confeval.py"
        confeval.write_text("")
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._load_confeval(tmp_path)
        assert result is via_fn

    def test_no_entry_point_returns_none(self, tmp_path: Path, cmd: EvalCommand) -> None:
        # confeval.py present but has neither get_eval_config nor EVAL_CONFIG
        fake_mod = types.SimpleNamespace()
        confeval = tmp_path / "confeval.py"
        confeval.write_text("")
        with patch.object(cmd, "_load_module", return_value=fake_mod):
            result = cmd._load_confeval(tmp_path)
        assert result is None

    def test_import_error_returns_none(self, tmp_path: Path, cmd: EvalCommand) -> None:
        confeval = tmp_path / "confeval.py"
        confeval.write_text("")
        with patch.object(cmd, "_load_module", side_effect=ImportError("bad")):
            result = cmd._load_confeval(tmp_path)
        assert result is None


# ── confeval.py discovery (independent of target) ───────────────────────────────


class TestConfevalDiscovery:
    """confeval.py is the global config; discovery must not depend on the target.

    Regression: targeting a single eval file used to look for
    `<file>/confeval.py`, which never exists, so files without a per-file
    config silently fell back to built-in defaults instead of the global
    confeval.py.
    """

    def test_search_dirs_walks_up_from_file(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        evals_dir = tmp_path / "evals"
        sub = evals_dir / "sub"
        sub.mkdir(parents=True)
        target = sub / "weather_eval.py"
        target.write_text("")
        dirs = cmd._confeval_search_dirs(target, evals_dir)
        # Parent of the file is searched first, walking up; the evals dir is included.
        assert dirs[0] == sub.resolve()
        assert evals_dir.resolve() in dirs

    def test_search_dirs_includes_evals_dir_for_directory_target(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        evals_dir = tmp_path / "evals"
        evals_dir.mkdir()
        dirs = cmd._confeval_search_dirs(evals_dir, evals_dir)
        assert evals_dir.resolve() in dirs

    def test_resolve_confeval_finds_for_single_file_target(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        evals_dir = tmp_path / "evals"
        evals_dir.mkdir()
        target_file = evals_dir / "weather_eval.py"
        target_file.write_text("")
        expected = EvalConfig()

        # confeval.py lives in the evals dir, not alongside nothing under the file.
        def fake_load(d: Path):
            return expected if d.resolve() == evals_dir.resolve() else None

        with patch.object(cmd, "_load_confeval", side_effect=fake_load):
            cfg, path = cmd._resolve_confeval(target_file, evals_dir)

        assert cfg is expected
        assert path == evals_dir / "confeval.py"

    def test_resolve_confeval_returns_none_when_absent(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        evals_dir = tmp_path / "evals"
        evals_dir.mkdir()
        target_file = evals_dir / "weather_eval.py"
        target_file.write_text("")
        with patch.object(cmd, "_load_confeval", return_value=None):
            cfg, path = cmd._resolve_confeval(target_file, evals_dir)
        assert cfg is None
        assert path is None


# ── _collect_from_file ────────────────────────────────────────────────────────


class TestCollectFromFile:
    """Test per-file collection using config priority chain."""

    def _dummy_path(self, tmp_path: Path) -> Path:
        p = tmp_path / "x_eval.py"
        p.write_text("")
        return p

    def _fake_eval_set(self) -> MagicMock:
        es = MagicMock()
        es.cases = [MagicMock()]
        return es

    def test_file_config_takes_priority_over_global_config(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        from agentflow.qa.evaluation import EvalConfig

        global_cfg = EvalConfig()
        file_cfg = EvalConfig()
        fake_es = self._fake_eval_set()
        fake_pending = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            EVAL_CONFIG=file_cfg,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_make_pending", return_value=fake_pending) as mock_make,
        ):
            result = cmd._collect_from_file(self._dummy_path(tmp_path), global_cfg)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is file_cfg
        assert used_config is not global_cfg
        assert used_source == "per-file"
        assert result == fake_pending

    def test_file_config_used_when_no_global(self, tmp_path: Path, cmd: EvalCommand) -> None:
        from agentflow.qa.evaluation import EvalConfig

        file_cfg = EvalConfig()
        fake_es = self._fake_eval_set()
        fake_pending = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            EVAL_CONFIG=file_cfg,
            app=MagicMock(),
        )
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_make_pending", return_value=fake_pending) as mock_make,
        ):
            result = cmd._collect_from_file(self._dummy_path(tmp_path), None)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is file_cfg
        assert used_source == "per-file"

    def test_default_config_used_when_no_configs(self, tmp_path: Path, cmd: EvalCommand) -> None:
        from agentflow.qa.evaluation import EvalConfig

        fake_es = self._fake_eval_set()
        fake_pending = [MagicMock()]
        fake_mod = types.SimpleNamespace(
            get_eval_set=lambda: fake_es,
            app=MagicMock(),
        )
        default_cfg = EvalConfig()
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_default_config", return_value=default_cfg),
            patch.object(cmd, "_make_pending", return_value=fake_pending) as mock_make,
        ):
            result = cmd._collect_from_file(self._dummy_path(tmp_path), None)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is default_cfg
        assert used_source == "built-in defaults"

    def test_no_entry_point_returns_empty_and_warns(
        self, tmp_path: Path, cmd: EvalCommand
    ) -> None:
        fake_mod = types.SimpleNamespace()
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(cmd, "_collect_eval_functions", return_value=([], None)),
        ):
            result = cmd._collect_from_file(self._dummy_path(tmp_path), None)

        assert result == []
        assert any("skip" in w.lower() for w in cmd.output.warnings)  # type: ignore[attr-defined]

    def test_pytest_style_discovery_fallback(self, tmp_path: Path, cmd: EvalCommand) -> None:
        from agentflow.qa.evaluation import EvalConfig

        fake_es = self._fake_eval_set()
        fake_pending = [MagicMock()]
        global_cfg = EvalConfig()
        fake_mod = types.SimpleNamespace(app=MagicMock())
        with (
            patch.object(cmd, "_load_module", return_value=fake_mod),
            patch.object(
                cmd, "_collect_eval_functions", return_value=([("my_eval", fake_es)], None)
            ),
            patch.object(cmd, "_make_pending", return_value=fake_pending) as mock_make,
        ):
            result = cmd._collect_from_file(self._dummy_path(tmp_path), global_cfg)

        used_config = mock_make.call_args.args[2]
        used_source = mock_make.call_args.args[4]
        assert used_config is global_cfg
        assert used_source == "confeval.py"
        assert result == fake_pending


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
