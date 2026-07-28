"""Environment and project diagnostics for the Agentflow CLI."""

from __future__ import annotations

import importlib
import json
import socket
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import DEFAULT_PORT


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: str
    detail: str


class DoctorCommand(BaseCommand):
    """Inspect the local CLI, core package, project config, and default port."""

    def execute(self, **kwargs: Any) -> int:
        diagnostics = [
            Diagnostic("Python", "pass", sys.version.split()[0]),
            self._package_check("10xscale-agentflow-cli"),
            self._package_check("10xscale-agentflow"),
            self._evaluation_api_check(),
            self._config_check(),
            self._port_check(DEFAULT_PORT),
        ]
        self.output.command_header(
            "doctor",
            "Checking the current Agentflow development environment.",
            color="cyan",
        )
        self.output.print_table(
            ["Check", "Status", "Details"],
            [
                [item.name, self._status_label(item.status), item.detail]
                for item in diagnostics
            ],
            title="Diagnostics",
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
        try:
            installed = version(distribution)
        except PackageNotFoundError:
            return Diagnostic(distribution, "fail", "not installed")
        return Diagnostic(distribution, "pass", installed)

    @staticmethod
    def _evaluation_api_check() -> Diagnostic:
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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return Diagnostic(f"Port {port}", "warn", "already in use")
        return Diagnostic(f"Port {port}", "pass", "available")

    @staticmethod
    def _status_label(status: str) -> str:
        return {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[status]
