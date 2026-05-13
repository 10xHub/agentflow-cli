"""Test command implementation — thin pytest wrapper."""

import subprocess  # nosec: B404
import sys
import webbrowser
from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.core.config import ConfigManager


class TestCommand(BaseCommand):
    """Run the project's test suite via pytest."""

    def execute(
        self,
        path: str | None = None,
        coverage: bool = False,
        html: bool = False,
        keyword: str | None = None,
        verbose: bool = False,
        quiet: bool = False,
        extra_args: tuple[str, ...] = (),
        **kwargs: Any,
    ) -> int:
        project_root = Path.cwd()

        # Load optional overrides from agentflow.json
        cfg: dict[str, Any] = {}
        config_manager = ConfigManager()
        discovered = config_manager.auto_discover_config()
        if discovered:
            try:
                config_manager.load_config(str(discovered))
                cfg = config_manager.get_test_config()
            except Exception:  # nosec: B110
                self.logger.warning("Failed to load test configuration from %s", discovered)

        # Explicit CLI path wins; fall back to agentflow.json; None = pytest auto-discovery
        resolved_path: str | None = path or cfg.get("path") or None
        resolved_coverage = coverage or cfg.get("coverage", False)
        coverage_threshold: int | None = cfg.get("coverage_threshold")

        location = str(project_root / resolved_path) if resolved_path else str(project_root)
        self.output.print_banner("Test", f"Running tests in {location}")

        cmd = [sys.executable, "-m", "pytest"]
        if resolved_path:
            cmd.append(resolved_path)

        if verbose:
            cmd.append("-v")
        elif quiet:
            cmd.append("-q")
        else:
            cmd.append("-v")

        if resolved_coverage:
            cmd += [
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
            ]
            if coverage_threshold is not None:
                cmd.append(f"--cov-fail-under={coverage_threshold}")

        if keyword:
            cmd += ["-k", keyword]

        cmd += list(extra_args)

        self.logger.info("Running: %s", " ".join(cmd))

        result = subprocess.run(cmd, cwd=project_root, check=False)  # nosec: B603  # noqa: S603

        if result.returncode == 0:
            self.output.success("All tests passed.")
        else:
            self.output.error(f"Tests finished with exit code {result.returncode}.")

        if html and resolved_coverage:
            report_path = (project_root / "htmlcov" / "index.html").as_uri()
            self.output.info(f"Opening coverage report: {report_path}", emoji=False)
            webbrowser.open(report_path)

        return result.returncode
