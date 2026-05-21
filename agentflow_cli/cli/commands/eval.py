"""Eval command — discover and run agentflow evaluations, always generating reports."""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import sys
import typing
import webbrowser
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentflow.qa.evaluation import CriteriaConfig, CriterionConfig, EvalConfig
from agentflow.qa.evaluation.collectors.trajectory_collector import (
    TrajectoryCollector,
    make_trajectory_callback,
)
from agentflow.qa.evaluation.config.eval_config import ReporterConfig
from agentflow.qa.evaluation.eval_result import EvalCaseResult
from agentflow.qa.evaluation.eval_result import EvalReport as ER
from agentflow.qa.evaluation.evaluator import AgentEvaluator
from agentflow.qa.evaluation.reporters.manager import ReporterManager
from agentflow.utils.callbacks import CallbackManager
from injectq.testing import override_dependency

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.core.config import ConfigManager


if TYPE_CHECKING:
    from agentflow.qa.evaluation.eval_result import EvalReport


@dataclass
class _PendingCase:
    case: Any  # EvalCase
    evaluator: AgentEvaluator
    file_name: str
    eval_set_id: str
    eval_set_name: str


@dataclass
class _PendingSimulation:
    scenario: Any  # ConversationScenario
    graph: Any
    simulator: Any  # UserSimulator
    file_name: str
    eval_set_id: str
    eval_set_name: str


def _reset_inject_proxy(service_type: type) -> None:
    """Reset the lazy Inject[T] proxy cached on Node.execute's default parameters.

    Inject[T] proxies cache their resolved value in _injected_value on first use.
    container.override() clears the singleton scope, but the proxy's own cache is
    independent — it must be cleared so the proxy re-resolves from the container
    on next invocation instead of returning the stale value.
    """
    try:
        from agentflow.core.graph.node import Node as _GraphNode

        defaults = getattr(_GraphNode.execute, "__defaults__", None) or ()
        for d in defaults:
            if (
                hasattr(d, "_injected_value")
                and hasattr(d, "service_type")
                and d.service_type is service_type
            ):
                d._injected_value = None
    except Exception:  # nosec B110  # noqa: S110
        pass


DEFAULT_CONCURRENCY = 4


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
    # Default config
    # ------------------------------------------------------------------

    def _default_config(self) -> EvalConfig:
        return EvalConfig(
            criteria=CriteriaConfig(
                tool_name_match=CriterionConfig.tool_name_match(threshold=1.0),
                # response_match=CriterionConfig.response_match(threshold=0.8),
                # hallucinations=CriterionConfig.hallucination(threshold=0.8),
                rouge_match=CriterionConfig.rouge_match(threshold=0.5),
                node_order=CriterionConfig.node_order(threshold=0.8),
            )
        )

    # ------------------------------------------------------------------
    # confeval.py loading
    # ------------------------------------------------------------------

    def _load_confeval(self, evals_dir: Path) -> EvalConfig | None:
        """Find and load confeval.py from evals_dir, returning its EvalConfig.

        Tries get_eval_config() first, then falls back to the EVAL_CONFIG
        constant.  Returns None if no confeval.py is found so callers can
        distinguish "no confeval" from "confeval with empty criteria".
        """
        confeval_path = evals_dir / "confeval.py"
        if not confeval_path.exists():
            return None

        try:
            mod = self._load_module(confeval_path)
        except Exception as exc:
            self.logger.warning("Failed to load confeval.py: %s", exc)
            return None

        if hasattr(mod, "get_eval_config"):
            try:
                return mod.get_eval_config()
            except Exception as exc:
                self.logger.warning("get_eval_config() in confeval.py failed: %s", exc)

        if hasattr(mod, "EVAL_CONFIG"):
            return mod.EVAL_CONFIG

        self.logger.warning(
            "confeval.py found but has no get_eval_config() or EVAL_CONFIG — ignoring"
        )
        return None

    def _collect_eval_functions(self, mod: Any) -> tuple[list[tuple[str, Any]], Any]:
        """Pytest-style discovery: functions annotated -> EvalSet are evals, ->
        EvalConfig is config."""
        from agentflow.qa.evaluation import EvalConfig, EvalSet

        eval_pairs: list[tuple[str, Any]] = []
        config: Any = None

        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("_"):
                continue
            if getattr(obj, "__module__", None) != getattr(mod, "__name__", None):
                continue
            hints: dict[str, Any] = {}
            try:
                hints = typing.get_type_hints(obj)
            except Exception:
                hints = getattr(obj, "__annotations__", {})

            ret = hints.get("return")
            if ret is None:
                continue

            try:
                if inspect.isclass(ret) and issubclass(ret, EvalSet):
                    eval_pairs.append((name, obj()))
                    continue
                if inspect.isclass(ret) and issubclass(ret, EvalConfig) and config is None:
                    config = obj()
            except Exception as exc:
                self.logger.warning("Could not call %s(): %s", name, exc)

        return eval_pairs, config

    # ------------------------------------------------------------------
    # Flat pool: collect all pending cases from a file
    # ------------------------------------------------------------------

    def _collect_from_file(
        self, path: Path, global_config: EvalConfig | None
    ) -> list[_PendingCase | _PendingSimulation]:
        """Load a module and return pending work for every eval case or simulation scenario.

        Config priority chain (highest → lowest):
          1. confeval.py   — global_config (not None when confeval was found)
          2. Per-file      — EVAL_CONFIG / get_eval_config() inside the file
          3. Built-in defaults — _default_config()

        Returns _PendingSimulation items when the file exposes get_scenarios() or SCENARIOS.
        Returns _PendingCase items for the standard get_eval_set() / pytest-style protocols.
        """
        mod = self._load_module(path)
        file_name = path.name

        # Simulator protocol — get_scenarios() or SCENARIOS constant
        scenarios = None
        if hasattr(mod, "get_scenarios"):
            try:
                scenarios = mod.get_scenarios()
            except Exception as exc:
                self.logger.warning("Could not call get_scenarios() in %s: %s", file_name, exc)
        elif hasattr(mod, "SCENARIOS"):
            scenarios = mod.SCENARIOS

        if scenarios is not None:
            return self._collect_simulations(mod, scenarios, file_name)

        # get_eval_set() protocol
        if hasattr(mod, "get_eval_set"):
            file_config: EvalConfig | None = None
            if hasattr(mod, "get_eval_config"):
                file_config = mod.get_eval_config()
            elif hasattr(mod, "EVAL_CONFIG"):
                file_config = mod.EVAL_CONFIG
            # Priority: confeval > per-file > defaults
            config = global_config or file_config or self._default_config()
            return self._make_pending(mod, mod.get_eval_set(), config, file_name)

        # pytest-style discovery
        eval_pairs, discovered_config = self._collect_eval_functions(mod)
        if eval_pairs:
            file_config = discovered_config or (
                mod.get_eval_config()
                if hasattr(mod, "get_eval_config")
                else mod.EVAL_CONFIG
                if hasattr(mod, "EVAL_CONFIG")
                else None
            )
            # Priority: confeval > per-file > defaults
            config = global_config or file_config or self._default_config()
            pending: list[_PendingCase] = []
            for _, es in eval_pairs:
                pending.extend(self._make_pending(mod, es, config, file_name))
            return pending

        self.output.warning(f"Skipping {file_name} — no eval entry point found.")
        return []

    def _collect_simulations(
        self, mod: Any, scenarios: list[Any], file_name: str
    ) -> list[_PendingSimulation]:
        """Build _PendingSimulation items for each scenario in the file."""
        from agentflow.qa.evaluation import (
            CriterionConfig,
            SimulationGoalsCriterion,
            UserSimulator,
            UserSimulatorConfig,
        )

        graph = getattr(mod, "app", None) or self._load_agent_from_config()

        # Per-file simulator config via SIMULATOR_CONFIG constant or default
        sim_cfg: UserSimulatorConfig | None = getattr(mod, "SIMULATOR_CONFIG", None)
        goal_threshold: float = 0.7
        if sim_cfg is not None and hasattr(sim_cfg, "goal_threshold"):
            goal_threshold = sim_cfg.goal_threshold  # type: ignore[attr-defined]

        judge = SimulationGoalsCriterion(
            config=CriterionConfig(threshold=goal_threshold, num_samples=1)
        )
        simulator = UserSimulator(
            config=sim_cfg or UserSimulatorConfig(),
            criteria=[judge],
        )

        eval_set_id = f"{Path(file_name).stem}_simulations"
        eval_set_name = f"{Path(file_name).stem} (user simulator)"

        return [
            _PendingSimulation(
                scenario=sc,
                graph=graph,
                simulator=simulator,
                file_name=file_name,
                eval_set_id=eval_set_id,
                eval_set_name=eval_set_name,
            )
            for sc in scenarios
        ]

    def _make_pending(
        self, mod: Any, eval_set: Any, config: EvalConfig, file_name: str
    ) -> list[_PendingCase]:
        graph = getattr(mod, "app", None) or self._load_agent_from_config()
        collector = TrajectoryCollector(capture_all_events=True)
        evaluator = AgentEvaluator(graph, collector, config=config)
        return [
            _PendingCase(
                case=c,
                evaluator=evaluator,
                file_name=file_name,
                eval_set_id=eval_set.eval_set_id,
                eval_set_name=eval_set.name,
            )
            for c in eval_set.eval_cases
        ]

    # ------------------------------------------------------------------
    # Criteria display
    # ------------------------------------------------------------------

    def _print_criteria_block(
        self,
        confeval_config: EvalConfig | None,
        target_path: Path,
    ) -> None:
        """Print the active criteria and their source before any case runs."""
        if confeval_config is not None:
            source = str(target_path / "confeval.py")
            criteria = confeval_config.criteria
        else:
            source = "built-in defaults"
            criteria = self._default_config().criteria

        print(f"Criteria  source: {source}", flush=True)  # noqa: T201
        for name in criteria.model_fields:
            cfg = getattr(criteria, name)
            if cfg is None:
                continue

            parts = [f"threshold={cfg.threshold}"]
            parts.append(cfg.match_type.value)
            if cfg.judge_model:
                parts.append(f"judge={cfg.judge_model}")
            if cfg.num_samples and cfg.num_samples != 1:
                parts.append(f"samples={cfg.num_samples}")
            print(f"  {name:<40} {'  '.join(parts)}", flush=True)  # noqa: T201
        print("", flush=True)  # noqa: T201

    # ------------------------------------------------------------------
    # Progress printing
    # ------------------------------------------------------------------

    def _print_case_progress(
        self,
        file_name: str,
        case_name: str,
        result: EvalCaseResult,
        index: int,
        total: int,
    ) -> None:
        status = "PASSED" if result.passed else ("ERROR" if result.is_error else "FAILED")
        duration = f"{result.duration_seconds:.2f}s"
        label = f"{file_name}::{case_name}"
        status_colored = f"\033[32m{status}\033[0m" if result.passed else f"\033[31m{status}\033[0m"
        tok = getattr(result, "token_usage", None)
        tok_str = ""
        if tok and (tok.input_tokens or tok.output_tokens):
            tok_str = f"  in={tok.input_tokens} out={tok.output_tokens}"
        print(f"[{index:3d}/{total}] {label}  {status_colored}  {duration}{tok_str}", flush=True)  # noqa: T201

    # ------------------------------------------------------------------
    # Flat pool execution — single asyncio event loop for all cases
    # ------------------------------------------------------------------

    async def _run_flat_pool(
        self,
        pending: list[_PendingCase | _PendingSimulation],
        max_concurrency: int,
        parallel: bool,
    ) -> list[tuple[str, str, str, EvalCaseResult]]:
        """Run all cases and simulations under a single event loop.

        Returns list of (file_name, eval_set_id, eval_set_name, EvalCaseResult).
        """
        total = len(pending)
        completed = 0

        async def _run_case(pc: _PendingCase) -> tuple[str, str, str, EvalCaseResult]:
            local_collector = TrajectoryCollector(
                capture_all_events=pc.evaluator.collector.capture_all_events,
            )
            _, local_mgr = make_trajectory_callback(local_collector)
            container = pc.evaluator.graph._state_graph._container
            # The Inject[CallbackManager] proxy on Node.execute caches its resolved
            # value independently of the container — reset it so it re-resolves
            # inside the override context instead of returning the stale instance.
            _reset_inject_proxy(CallbackManager)
            with override_dependency(CallbackManager, local_mgr, container=container):
                try:
                    result = await pc.evaluator._evaluate_case(
                        pc.case, collector_override=local_collector
                    )
                except Exception as exc:
                    result = EvalCaseResult.failure(
                        eval_id=pc.case.eval_id,
                        error=str(exc),
                        name=pc.case.name,
                    )
            return (pc.file_name, pc.eval_set_id, pc.eval_set_name, result)

        async def _run_simulation(ps: _PendingSimulation) -> tuple[str, str, str, EvalCaseResult]:
            from agentflow.qa.evaluation.eval_result import CriterionResult
            from agentflow.qa.evaluation.token_usage import TokenUsage

            try:
                sim_result = await ps.simulator.run(ps.graph, ps.scenario)
                # Use the full CriterionResult objects (with per-criterion token_usage)
                # if available; fall back to rebuilding from scores dict.
                criterion_results = sim_result.criterion_results or [
                    CriterionResult.success(
                        criterion=name,
                        score=score,
                        threshold=ps.simulator.criteria[0].threshold
                        if ps.simulator.criteria
                        else 0.7,
                        details=sim_result.criterion_details.get(name, {}),
                    )
                    for name, score in sim_result.criterion_scores.items()
                ]
                # If no criterion ran (no goals defined), fall back to completion flag
                if not criterion_results:
                    score = 1.0 if sim_result.completed else 0.0
                    criterion_results = [
                        CriterionResult.success(
                            criterion="simulation_completed",
                            score=score,
                            threshold=0.5,
                        )
                    ]
                conversation_text = "\n".join(
                    f"{m['role'].upper()}: {m['content']}" for m in sim_result.conversation
                )
                criteria_token_usage = sum(
                    (cr.token_usage for cr in criterion_results), TokenUsage()
                )
                total_token_usage = sim_result.simulator_token_usage + criteria_token_usage
                result = EvalCaseResult.success(
                    eval_id=ps.scenario.scenario_id,
                    name=ps.scenario.description or ps.scenario.scenario_id,
                    criterion_results=criterion_results,
                    actual_response=conversation_text,
                    token_usage=total_token_usage,
                    agent_token_usage=sim_result.simulator_token_usage,
                    metadata={
                        "turns": sim_result.turns,
                        "goals_achieved": sim_result.goals_achieved,
                        "completed": sim_result.completed,
                    },
                )
            except Exception as exc:
                result = EvalCaseResult.failure(
                    eval_id=ps.scenario.scenario_id,
                    error=str(exc),
                    name=ps.scenario.description or ps.scenario.scenario_id,
                )
            return (ps.file_name, ps.eval_set_id, ps.eval_set_name, result)

        async def _dispatch(
            item: _PendingCase | _PendingSimulation,
        ) -> tuple[str, str, str, EvalCaseResult]:
            if isinstance(item, _PendingSimulation):
                return await _run_simulation(item)
            return await _run_case(item)

        if not parallel:
            results: list[tuple[str, str, str, EvalCaseResult]] = []
            for item in pending:
                quad = await _dispatch(item)
                completed += 1
                file_name, _, _, result = quad
                self._print_case_progress(
                    file_name, result.name or result.eval_id, result, completed, total
                )
                results.append(quad)
            return results

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run_one(
            item: _PendingCase | _PendingSimulation,
        ) -> tuple[str, str, str, EvalCaseResult]:
            async with semaphore:
                return await _dispatch(item)

        output_results: list[tuple[str, str, str, EvalCaseResult]] = []
        tasks = [asyncio.create_task(_run_one(item)) for item in pending]
        for coro in asyncio.as_completed(tasks):
            quad = await coro
            completed += 1
            file_name, _, _, result = quad
            self._print_case_progress(
                file_name, result.name or result.eval_id, result, completed, total
            )
            output_results.append(quad)

        return output_results

    # ------------------------------------------------------------------
    # Report merging
    # ------------------------------------------------------------------

    def _merge_reports(self, reports: list[EvalReport]) -> EvalReport:
        if len(reports) == 1:
            return reports[0]

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
                self.logger.warning(
                    "Failed to load eval directory from config; using default 'evals/'"
                )
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
        parallel: bool = False,
        max_concurrency: int = 4,
        verbose: bool = False,
        quiet: bool = False,
        **kwargs: Any,
    ) -> int:
        # 1. Load infra settings from agentflow.json — no criteria here.
        # Criteria come exclusively from confeval.py (step 4) or per-file config.
        config_manager = ConfigManager()
        discovered = config_manager.auto_discover_config()
        json_directory = "evals"
        effective_parallel = parallel
        effective_concurrency = max_concurrency
        if discovered:
            try:
                config_manager.load_config(str(discovered))
                global_eval_cfg = config_manager.get_evaluation_config()
                if output_dir == "eval_reports":
                    output_dir = global_eval_cfg.get("output_dir", output_dir)
                if threshold is None:
                    threshold = global_eval_cfg.get("threshold")
                if not parallel:
                    effective_parallel = global_eval_cfg.get("parallel", False)
                if max_concurrency == DEFAULT_CONCURRENCY:
                    effective_concurrency = global_eval_cfg.get(
                        "max_concurrency", DEFAULT_CONCURRENCY
                    )
                json_directory = global_eval_cfg.get("directory", json_directory)
            except Exception:
                self.logger.warning(
                    "Failed to load eval config from agentflow.json; using defaults"
                )

        # 2. CLI flags already captured as function parameters (highest priority).

        # 3. Resolve target path
        if target:
            target_path = Path(target)
            if not target_path.exists():
                self.output.error(f"Path not found: {target}")
                return 1
        else:
            target_path = Path.cwd() / json_directory
            if not target_path.exists():
                self.output.error(
                    f"Eval directory '{target_path}' not found. "
                    "Create an evals/ directory or pass a file/folder path."
                )
                return 1

        # 4. Load confeval.py → global criteria config (None if not found)
        confeval_config = self._load_confeval(target_path)

        # 5. Discover files
        files = self._discover(target_path)
        if not files:
            self.output.error(f"No eval files found in {target_path}")
            return 1

        # 6. Collect all pending cases across every file
        pending: list[_PendingCase] = []
        for f in files:
            try:
                cases = self._collect_from_file(f, confeval_config)
                pending.extend(cases)
            except Exception as exc:
                self.output.error(f"Error loading {f.name}: {exc}")
                self.logger.exception("Failed to load eval file: %s", f)

        if not pending:
            self.output.error(
                "No eval cases found. Ensure eval files expose get_eval_set() "
                "or functions annotated with -> EvalSet."
            )
            return 1

        n_files = len({pc.file_name for pc in pending})
        n_sims = sum(1 for pc in pending if isinstance(pc, _PendingSimulation))
        n_cases = len(pending) - n_sims
        parts = []
        if n_cases:
            parts.append(f"{n_cases} eval case(s)")
        if n_sims:
            parts.append(f"{n_sims} simulation scenario(s)")
        self.output.print_banner(
            "Eval",
            f"Found {', '.join(parts)} across {n_files} file(s) in {target_path}",
        )

        # 7. Print criteria block so users know what is being evaluated
        self._print_criteria_block(confeval_config, target_path)

        # 8. Run all cases under a single asyncio event loop
        quads = asyncio.run(self._run_flat_pool(pending, effective_concurrency, effective_parallel))

        if not quads:
            self.output.error("No results produced.")
            return 1

        # 7. Group by eval_set_id → one EvalReport per set
        groups: dict[str, tuple[str, list[EvalCaseResult]]] = defaultdict(lambda: ("", []))
        for _, eval_set_id, eval_set_name, result in quads:
            name, results_list = groups[eval_set_id]
            groups[eval_set_id] = (eval_set_name or name, [*results_list, result])

        reports: list[EvalReport] = []
        for eval_set_id, (eval_set_name, results) in groups.items():
            reports.append(
                ER.create(
                    eval_set_id=eval_set_id,
                    eval_set_name=eval_set_name,
                    results=results,
                    config_used=(confeval_config or self._default_config()).model_dump(),
                )
            )

        # 8. Merge into a single report
        merged = self._merge_reports(reports)

        # 9. Determine exit code
        if threshold is not None and merged.summary.pass_rate < threshold:
            self.output.error(
                f"Pass rate {merged.summary.pass_rate:.1%} is below threshold {threshold:.1%}"
            )
            return_code = 1
        else:
            return_code = 0 if merged.summary.pass_rate == 1.0 else 1

        # 10. Generate reports
        if not no_report:
            manager = ReporterManager(
                ReporterConfig(
                    output_dir=output_dir,
                    html=True,
                    json_report=True,
                    console=False,
                    timestamp_files=True,
                )
            )
            report_result = manager.run_all(merged)

            if report_result.html_path:
                self.output.success(f"HTML report: {report_result.html_path}")
            if report_result.json_path:
                self.output.info(f"JSON report: {report_result.json_path}", emoji=False)
            if report_result.has_errors:
                for name, err in report_result.errors:
                    self.output.warning(f"Reporter error [{name}]: {err}")

            if open_report and report_result.html_path:
                webbrowser.open(Path(report_result.html_path).as_uri())

        summary = merged.summary
        self.output.info(
            f"Results: {summary.passed_cases}/{summary.total_cases} passed "
            f"({summary.pass_rate:.1%})",
            emoji=False,
        )
        tok = summary.total_token_usage
        if tok.total_tokens:
            cache_part = f"  cache_read: {tok.cache_read_tokens:,}" if tok.cache_read_tokens else ""
            self.output.info(
                f"Tokens  — input: {tok.input_tokens:,}  output: {tok.output_tokens:,}"
                f"{cache_part}  total: {tok.total_tokens:,}",
                emoji=False,
            )

        return return_code
