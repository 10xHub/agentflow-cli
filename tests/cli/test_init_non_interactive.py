"""Non-interactive and dry-run project initialization."""

from __future__ import annotations

import io
from pathlib import Path

from agentflow_cli.cli.commands.init import InitCommand
from agentflow_cli.cli.core.output import OutputFormatter


def test_dry_run_does_not_create_target(tmp_path: Path) -> None:
    target = tmp_path / "preview-agent"
    stream = io.StringIO()
    command = InitCommand(OutputFormatter(stream=stream))

    result = command.execute(
        path=str(target),
        agent_name="Preview Agent",
        template="production",
        auth="jwt",
        rate_limit="redis",
        non_interactive=True,
        dry_run=True,
    )

    assert result == 0
    assert not target.exists()
    assert "Files that would be created" in stream.getvalue()
    assert "no files were written" in stream.getvalue()


def test_non_interactive_quick_start_creates_project(tmp_path: Path) -> None:
    target = tmp_path / "weather-agent"
    command = InitCommand(OutputFormatter(stream=io.StringIO()))

    result = command.execute(
        path=str(target),
        agent_name="Weather Agent",
        template="quick-start",
        non_interactive=True,
    )

    assert result == 0
    assert (target / "agentflow.json").exists()
    assert (target / "graph" / "agent.py").exists()


def test_non_interactive_rejects_production_options_on_quick_start(tmp_path: Path) -> None:
    command = InitCommand(OutputFormatter(stream=io.StringIO()))
    result = command.execute(
        path=str(tmp_path / "invalid"),
        template="quick-start",
        auth="jwt",
        non_interactive=True,
    )
    assert result != 0
