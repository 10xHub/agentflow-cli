"""Eval command — discover and run agentflow evaluations, always generating reports."""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import sys
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.core.config import ConfigManager


if TYPE_CHECKING:
    from agentflow.qa.evaluation.eval_result import EvalReport


class EvalCommand(BaseCommand):
    """Discover and run agent evaluations; always write HTML + JSON reports."""

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover(self, target: Path) -> list[Path]:
        """Return eval files under target. If target is a file, return it directly."""
        if target.is_file():
            return [target]

        seen: dict[Path, None] = {}
        for pattern in ("*_eval.py", "eval_*.py"):
            for p in sorted(target.rglob(pattern)):
                seen[p] = None
        return list(seen)

    # ------------------------------------------------------------------
    # Module loading
    # ------------------------------------------------------------------

    def _load_module(self, path: Path) -> Any:
        project_root = str(Path.cwd())
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        spec = importlib.util.spec_from_file_location("_agentflow_eval", path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    # ------------------------------------------------------------------
    # Agent loading from agentflow.json
    # ------------------------------------------------------------------

    def _load_agent_from_config(self) -> Any:
        config_manager = ConfigManager()
        discovered = config_manager.auto_discover_config()
        if not discovered:
            raise RuntimeError("No agentflow.json found — cannot auto-load agent.")
        config_manager.load_config(str(discovered))
        agent_spec: str = config_manager.get_config_value("agent", default="")
        if not agent_spec or ":" not in agent_spec:
            raise RuntimeError(f"Invalid 'agent' field in agentflow.json: {agent_spec!r}")
        module_path, attr = agent_spec.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)

    # ------------------------------------------------------------------
    # Per-file runner (sync wrapper — avoids nested asyncio.run() issues)
    # ------------------------------------------------------------------

    def _run_file_sync(self, path: Path) -> EvalReport | None:
        """Load and run a single eval file. Returns EvalReport or None if skipped."""
        self.output.info(f"Running: {path.name}", emoji=False)
        mod = self._load_module(path)

        # Option A: run() function — module has full control
        if hasattr(mod, "run"):
            result = mod.run()
            if inspect.isawaitable(result):
                return asyncio.run(result)
            return result  # type: ignore[return-value]

        # Option B: get_eval_set() + get_eval_config() — CLI loads agent
        if hasattr(mod, "get_eval_set") and hasattr(mod, "get_eval_config"):
            return self._run_with_evaluator(mod, mod.get_eval_set(), mod.get_eval_config())

        # Option C: EVAL_CONFIG constant + get_eval_set()
        if hasattr(mod, "EVAL_CONFIG") and hasattr(mod, "get_eval_set"):
            return self._run_with_evaluator(mod, mod.get_eval_set(), mod.EVAL_CONFIG)

        self.output.warning(
            f"Skipping {path.name} — no run(), get_eval_set()+get_eval_config(), "
            "or EVAL_CONFIG+get_eval_set() found."
        )
        return None

    def _run_with_evaluator(self, mod: Any, eval_set: Any, config: Any) -> EvalReport:
        from agentflow.qa.evaluation.collectors.trajectory_collector import TrajectoryCollector
        from agentflow.qa.evaluation.evaluator import AgentEvaluator

        # Prefer the graph already imported in the module (most common pattern)
        graph = getattr(mod, "app", None) or self._load_agent_from_config()
        collector = TrajectoryCollector(capture_all_events=True)
        evaluator = AgentEvaluator(graph, collector, config=config)
        return asyncio.run(evaluator.evaluate(eval_set))

    # ------------------------------------------------------------------
    # Report merging
    # ------------------------------------------------------------------

    def _merge_reports(self, reports: list[EvalReport]) -> EvalReport:
        if len(reports) == 1:
            return reports[0]

        from agentflow.qa.evaluation.eval_result import EvalReport as ER

        all_results = []
        for r in reports:
            all_results.extend(r.results)
        return ER.create(
            eval_set_id="combined_eval",
            eval_set_name="Combined Evaluation",
            results=all_results,
        )

    # ------------------------------------------------------------------
    # Eval directory from agentflow.json
    # ------------------------------------------------------------------

    def _resolve_eval_dir(self) -> Path:
        config_manager = ConfigManager()
        discovered = config_manager.auto_discover_config()
        directory = "evals"
        if discovered:
            try:
                config_manager.load_config(str(discovered))
                eval_cfg = config_manager.get_evaluation_config()
                directory = eval_cfg.get("directory", "evals")
            except Exception:
                pass
        return Path.cwd() / directory

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def execute(  # noqa: PLR0912, PLR0915
        self,
        target: str | None = None,
        output_dir: str = "eval_reports",
        no_report: bool = False,
        threshold: float | None = None,
        open_report: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        **kwargs: Any,
    ) -> int:
        # Load optional overrides from agentflow.json
        config_manager = ConfigManager()
        discovered = config_manager.auto_discover_config()
        if discovered:
            try:
                config_manager.load_config(str(discovered))
                eval_cfg = config_manager.get_evaluation_config()
                if output_dir == "eval_reports":
                    output_dir = eval_cfg.get("output_dir", output_dir)
                if threshold is None:
                    threshold = eval_cfg.get("threshold")
            except Exception:
                pass

        # Resolve target path
        if target:
            target_path = Path(target)
            if not target_path.exists():
                self.output.error(f"Path not found: {target}")
                return 1
        else:
            target_path = self._resolve_eval_dir()
            if not target_path.exists():
                self.output.error(
                    f"Eval directory '{target_path}' not found. "
                    "Create an evals/ directory or pass a file/folder path."
                )
                return 1

        files = self._discover(target_path)
        if not files:
            self.output.error(f"No eval files found in {target_path}")
            return 1

        self.output.print_banner("Eval", f"Found {len(files)} eval file(s) in {target_path}")

        # Run each file
        reports: list[EvalReport] = []
        for f in files:
            try:
                report = self._run_file_sync(f)
                if report is not None:
                    reports.append(report)
            except Exception as exc:
                self.output.error(f"Error in {f.name}: {exc}")
                self.logger.exception("Eval file failed: %s", f)

        if not reports:
            self.output.error("No reports produced. Ensure eval files expose run().")
            return 1

        merged = self._merge_reports(reports)

        # Determine exit code
        if threshold is not None and merged.summary.pass_rate < threshold:
            self.output.error(
                f"Pass rate {merged.summary.pass_rate:.1%} is below "
                f"threshold {threshold:.1%}"
            )
            return_code = 1
        else:
            return_code = 0 if merged.summary.pass_rate == 1.0 else 1

        # Always generate file reports unless --no-report
        if not no_report:
            from agentflow.qa.evaluation.config.eval_config import ReporterConfig
            from agentflow.qa.evaluation.reporters.manager import ReporterManager

            manager = ReporterManager(
                ReporterConfig(
                    output_dir=output_dir,
                    html=True,
                    json_report=True,
                    console=False,  # console output already handled by run() modules
                    timestamp_files=True,
                )
            )
            result = manager.run_all(merged)

            if result.html_path:
                self.output.success(f"HTML report: {result.html_path}")
            if result.json_path:
                self.output.info(f"JSON report: {result.json_path}", emoji=False)
            if result.has_errors:
                for name, err in result.errors:
                    self.output.warning(f"Reporter error [{name}]: {err}")

            if open_report and result.html_path:
                webbrowser.open(Path(result.html_path).as_uri())

        summary = merged.summary
        self.output.info(
            f"Results: {summary.passed_cases}/{summary.total_cases} passed "
            f"({summary.pass_rate:.1%})",
            emoji=False,
        )

        return return_code
