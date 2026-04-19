"""Tests for `agentflow skill` command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import agentflow_cli.cli.main as main_mod
from agentflow_cli.cli.templates.skills import SKILL_TARGETS


runner = CliRunner()


def test_skill_all_writes_every_target(tmp_path: Path) -> None:
    result = runner.invoke(main_mod.app, ["skill", "--path", str(tmp_path)])

    assert result.exit_code == 0, result.output
    for rel_path, _ in SKILL_TARGETS.values():
        assert (tmp_path / rel_path).exists()

    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# AgentFlow" in claude
    assert "provider=" in claude


def test_skill_single_agent_writes_only_that_file(tmp_path: Path) -> None:
    result = runner.invoke(
        main_mod.app,
        ["skill", "--path", str(tmp_path), "--agent", "cursor"],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".cursor" / "rules" / "agentflow.mdc").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()


def test_skill_cursor_has_frontmatter(tmp_path: Path) -> None:
    result = runner.invoke(
        main_mod.app,
        ["skill", "--path", str(tmp_path), "--agent", "cursor"],
    )
    assert result.exit_code == 0, result.output

    content = (tmp_path / ".cursor" / "rules" / "agentflow.mdc").read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "alwaysApply: true" in content


def test_skill_refuses_existing_file_without_force(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("existing", encoding="utf-8")

    result = runner.invoke(
        main_mod.app,
        ["skill", "--path", str(tmp_path), "--agent", "claude"],
    )

    assert result.exit_code != 0
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == "existing"


def test_skill_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("existing", encoding="utf-8")

    result = runner.invoke(
        main_mod.app,
        ["skill", "--path", str(tmp_path), "--agent", "claude", "--force"],
    )

    assert result.exit_code == 0, result.output
    new_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert new_content != "existing"
    assert "# AgentFlow" in new_content


def test_skill_unknown_agent_fails(tmp_path: Path) -> None:
    result = runner.invoke(
        main_mod.app,
        ["skill", "--path", str(tmp_path), "--agent", "does-not-exist"],
    )

    assert result.exit_code != 0
    assert "Unknown agent" in result.output
