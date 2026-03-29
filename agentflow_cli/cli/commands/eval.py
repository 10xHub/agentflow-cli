"""Eval command implementation.

Runs agent evaluation against an eval set and generates a JSON report
file in the current (or specified) directory.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import EvaluationError


class EvalCommand(BaseCommand):
    """Command to run agent evaluation and save a JSON report."""

    def execute(
        self,
        agent_module: str,
        eval_file: str,
        config_file: str | None = None,
        output: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Execute the eval command.

        Args:
            agent_module: Dotted Python module path containing the graph
                          (e.g. ``graph.react``).
            eval_file: Path to the ``.evalset.json`` file.
            config_file: Optional path to an ``EvalConfig`` JSON file.
            output: Output JSON file path.  Defaults to
                    ``eval_report_<timestamp>.json`` in the current directory.
            **kwargs: Additional arguments (unused).

        Returns:
            Exit code (0 = success).
        """
        try:
            self.output.print_banner(
                "Eval",
                "Running agent evaluation and generating JSON report",
                color="magenta",
            )

            # -- Validate inputs ------------------------------------------
            eval_path = Path(eval_file)
            if not eval_path.exists():
                raise EvaluationError(
                    f"Eval set file not found: {eval_file}",
                    agent_module=agent_module,
                    eval_file=eval_file,
                )

            if config_file and not Path(config_file).exists():
                raise EvaluationError(
                    f"Config file not found: {config_file}",
                    agent_module=agent_module,
                    eval_file=eval_file,
                )

            # -- Ensure the agent module is importable --------------------
            self._ensure_importable()

            # -- Determine output path ------------------------------------
            if output:
                output_path = Path(output)
            else:
                ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
                output_path = Path.cwd() / f"eval_report_{ts}.json"

            self.output.info(f"Agent module : {agent_module}")
            self.output.info(f"Eval file    : {eval_path.resolve()}")
            if config_file:
                self.output.info(f"Config file  : {Path(config_file).resolve()}")
            self.output.info(f"Output       : {output_path.resolve()}")

            # -- Run the evaluation ---------------------------------------
            self.output.info("Starting evaluation …")

            report = asyncio.run(
                self._run_evaluation(
                    agent_module=agent_module,
                    eval_file=str(eval_path),
                    config_file=config_file,
                )
            )

            # -- Write JSON report ----------------------------------------
            self._save_report(report, output_path)

            # -- Print summary --------------------------------------------
            summary = report.summary
            self.output.success(
                f"Evaluation complete — "
                f"{summary.passed_cases}/{summary.total_cases} passed "
                f"({summary.pass_rate:.0%})"
            )
            self.output.success(f"Report saved to {output_path.resolve()}")

            return 0

        except EvaluationError as e:
            return self.handle_error(e)
        except Exception as e:
            eval_error = EvaluationError(
                f"Evaluation failed: {e}",
                agent_module=agent_module,
                eval_file=eval_file,
            )
            return self.handle_error(eval_error)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_importable() -> None:
        """Insert CWD into ``sys.path`` so the agent module is importable."""
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

    @staticmethod
    async def _run_evaluation(
        agent_module: str,
        eval_file: str,
        config_file: str | None = None,
    ) -> Any:
        """Run the evaluation asynchronously using AgentEvaluator.

        Returns:
            An ``EvalReport`` instance.
        """
        from agentflow.evaluation.evaluator import AgentEvaluator

        return await AgentEvaluator.evaluate_file(
            agent_module=agent_module,
            eval_file=eval_file,
            config_file=config_file,
        )

    @staticmethod
    def _save_report(report: Any, path: Path) -> None:
        """Serialise and write the report JSON.

        Uses ``JSONReporter`` from the evaluation package when available,
        falling back to ``report.model_dump()`` + ``json.dumps()``.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from agentflow.evaluation.reporters.json import JSONReporter

            reporter = JSONReporter(indent=2)
            reporter.save(report, str(path))
        except ImportError:
            # Fallback: manual serialisation
            data = report.model_dump() if hasattr(report, "model_dump") else report
            path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
