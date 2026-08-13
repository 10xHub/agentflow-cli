"""Environment and project audit for the Agentflow CLI.

Backs ``agentflow audit``: a read-only pass over everything that has to be true
before ``agentflow dev``, ``eval``, or ``build`` can work in the current
directory. Nothing here mutates the project, the environment, or the user
configuration, so it is always safe to run.

Each check returns a :class:`Diagnostic` with one of three statuses:

``pass``
    The requirement is satisfied.
``warn``
    Not fatal for every workflow, but likely to surprise you. A missing
    ``agentflow.json`` is fine until you run ``agentflow dev``; a busy port is
    fine until you try to bind it.
``fail``
    A hard requirement is unmet and commands that depend on it will not run.

The command's exit code is the aggregate of those statuses (see
:meth:`AuditCommand.execute`), which is what makes it usable as a CI gate.
"""

from __future__ import annotations

import importlib
import json
import socket
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import DEFAULT_PORT


@dataclass(frozen=True)
class Diagnostic:
    """One audit result.

    Attributes:
        name: Human-readable label for the thing that was checked.
        status: One of ``"pass"``, ``"warn"``, or ``"fail"``.
        detail: Supporting evidence — a version, a path, or an error message.
    """

    name: str
    status: str
    detail: str


class AuditCommand(BaseCommand):
    """Audit the local CLI, core package, project config, and default port.

    Runs six checks in a fixed order and reports them twice: live, through the
    step timeline, and again as a summary table once every check has finished.

    ============  ==========================================================
    Check         What it asserts
    ============  ==========================================================
    python        The interpreter running the CLI (reported, never failed).
    cli           ``10xscale-agentflow-cli`` is installed and resolvable.
    core          ``10xscale-agentflow`` is installed and resolvable.
    evaluation    The installed core exposes the evaluation symbols that
                  ``agentflow eval`` imports, catching a CLI/core version
                  skew before it becomes an ImportError mid-run.
    config        ``agentflow.json`` exists here, parses, and declares an
                  ``agent`` key in ``module:attribute`` form.
    port          The default API port is free to bind.
    ============  ==========================================================
    """

    def execute(self, **kwargs: Any) -> int:
        """Run every check and report the outcome.

        Returns:
            ``1`` if any check failed, otherwise ``0`` — warnings are surfaced
            but do not fail the run, so ``agentflow audit`` can gate CI on
            hard breakage without tripping on an absent project config.
        """
        self.output.command_header(
            "audit",
            "Auditing the current Agentflow development environment.",
            color="cyan",
        )

        checks: tuple[tuple[str, str, Callable[[], Diagnostic]], ...] = (
            (
                "python",
                "Python interpreter",
                lambda: Diagnostic("Python", "pass", sys.version.split()[0]),
            ),
            ("cli", "CLI package", lambda: self._package_check("10xscale-agentflow-cli")),
            ("core", "Core framework", lambda: self._package_check("10xscale-agentflow")),
            ("evaluation", "Evaluation API", self._evaluation_api_check),
            ("config", "Project configuration", self._config_check),
            ("port", f"Port {DEFAULT_PORT}", lambda: self._port_check(DEFAULT_PORT)),
        )

        diagnostics: list[Diagnostic] = []
        timeline = self.output.timeline(
            "Running environment audit",
            steps=tuple((key, title) for key, title, _ in checks),
        )
        with timeline:
            for key, _title, run in checks:
                with timeline.step(key) as step:
                    result = run()
                    diagnostics.append(result)
                    step.detail(f"{self._status_label(result.status)}  {result.detail}")

        self.output.print_table(
            ["Check", "Status", "Details"],
            [[item.name, self._status_label(item.status), item.detail] for item in diagnostics],
            title="Audit results",
        )

        failures = [item for item in diagnostics if item.status == "fail"]
        warnings = [item for item in diagnostics if item.status == "warn"]
        if failures:
            self.output.error(f"{len(failures)} required check(s) failed.")
            return 1
        if warnings:
            self.output.warning(f"{len(warnings)} check(s) need attention.")
        else:
            self.output.completion_screen(
                "Environment ready",
                "All required Agentflow checks passed",
                details={"Checks": len(diagnostics), "Project": Path.cwd()},
            )
        return 0

    @staticmethod
    def _package_check(distribution: str) -> Diagnostic:
        """Report the installed version of ``distribution``, or fail if absent."""
        try:
            installed = version(distribution)
        except PackageNotFoundError:
            return Diagnostic(distribution, "fail", "not installed")
        return Diagnostic(distribution, "pass", installed)

    @staticmethod
    def _evaluation_api_check() -> Diagnostic:
        """Fail when the installed core lacks the symbols ``agentflow eval`` needs.

        This is the CLI/core version-skew check: both packages can be installed
        and still be incompatible, and without this the mismatch only surfaces
        as an ImportError partway through an evaluation run.
        """
        try:
            evaluation = importlib.import_module("agentflow.qa.evaluation")
        except ImportError as exc:
            return Diagnostic("Evaluation API", "fail", str(exc))

        required = ("CriteriaConfig", "CriterionConfig", "EvalConfig")
        missing = [name for name in required if not hasattr(evaluation, name)]
        if missing:
            return Diagnostic(
                "Evaluation API",
                "fail",
                "core package is missing: " + ", ".join(missing),
            )
        return Diagnostic("Evaluation API", "pass", "compatible")

    @staticmethod
    def _config_check() -> Diagnostic:
        """Validate ``agentflow.json`` in the working directory.

        Warns rather than fails when the file is absent, because the audit is
        also useful outside a project directory. A file that exists but cannot
        be parsed, or that omits a ``module:attribute`` ``agent`` key, is a
        hard failure.
        """
        config_path = Path.cwd() / "agentflow.json"
        if not config_path.exists():
            return Diagnostic("Project config", "warn", f"not found at {config_path}")
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return Diagnostic("Project config", "fail", str(exc))
        agent = data.get("agent")
        if not isinstance(agent, str) or ":" not in agent:
            return Diagnostic("Project config", "fail", "'agent' must be a module:attribute string")
        return Diagnostic("Project config", "pass", str(config_path))

    @staticmethod
    def _port_check(port: int) -> Diagnostic:
        """Warn when ``port`` on loopback already has a listener.

        A short connect probe, not a bind attempt, so the audit never steals
        the port from a server that is about to start.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return Diagnostic(f"Port {port}", "warn", "already in use")
        return Diagnostic(f"Port {port}", "pass", "available")

    @staticmethod
    def _status_label(status: str) -> str:
        """Render a status as the uppercase token used in the timeline and table."""
        return {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[status]
