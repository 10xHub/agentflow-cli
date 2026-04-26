"""Tests for the `agentflow skills` command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from agentflow_cli.cli.commands.skills import SkillsCommand
from agentflow_cli.cli.constants import CLI_VERSION
from agentflow_cli.cli.core.output import OutputFormatter


class _CapturingOutput(OutputFormatter):
    """Output formatter that records messages instead of printing."""

    def __init__(self) -> None:
        super().__init__()
        self.successes: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.tables: list[tuple[list[str], list[list[str]]]] = []
        self.lists: list[tuple[str | None, list[str]]] = []

    def print_banner(self, *args, **kwargs) -> None:  # type: ignore[override]
        return

    def success(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.successes.append(message)

    def error(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.errors.append(message)

    def warning(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.warnings.append(message)

    def info(self, message: str, emoji: bool = True) -> None:  # type: ignore[override]
        self.infos.append(message)

    def print_table(self, headers, rows, title=None) -> None:  # type: ignore[override]
        self.tables.append((headers, rows))

    def print_list(self, items, title=None, bullet="-") -> None:  # type: ignore[override]
        self.lists.append((title, list(items)))


@pytest.fixture
def out() -> _CapturingOutput:
    return _CapturingOutput()


@pytest.fixture
def cmd(out: _CapturingOutput) -> SkillsCommand:
    return SkillsCommand(output=out)


# --- agent normalisation -------------------------------------------------


def test_list_flag_prints_all_three_agents(cmd: SkillsCommand, out: _CapturingOutput) -> None:
    exit_code = cmd.execute(list_agents=True)
    assert exit_code == 0
    assert out.tables, "expected --list to print a table"
    headers, rows = out.tables[0]
    assert "Agent" in headers
    names = {row[0] for row in rows}
    assert names == {"Codex", "Claude", "GitHub"}


def test_invalid_agent_name_is_rejected(cmd: SkillsCommand, out: _CapturingOutput) -> None:
    exit_code = cmd.execute(agent="not-a-real-agent", path=".")
    assert exit_code != 0
    assert any("Invalid agent" in e for e in out.errors)


def test_all_with_explicit_agent_is_rejected(
    cmd: SkillsCommand, out: _CapturingOutput, tmp_path: Path
) -> None:
    exit_code = cmd.execute(agent="claude", all_agents=True, path=str(tmp_path))
    assert exit_code != 0
    assert any("--all cannot be combined with --agent" in e for e in out.errors)


# --- single-agent install -------------------------------------------------


def test_install_claude_creates_folder_and_manifest(
    cmd: SkillsCommand, tmp_path: Path
) -> None:
    exit_code = cmd.execute(agent="claude", path=str(tmp_path))
    assert exit_code == 0

    skill_dir = tmp_path / ".claude" / "skills" / "agentflow"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "references").is_dir()

    manifest = json.loads((skill_dir / ".agentflow-skill.json").read_text(encoding="utf-8"))
    assert manifest["agent"] == "Claude"
    assert manifest["cli_version"] == CLI_VERSION
    assert "installed_at" in manifest


def test_install_codex_uses_agents_dotdir(cmd: SkillsCommand, tmp_path: Path) -> None:
    exit_code = cmd.execute(agent="codex", path=str(tmp_path))
    assert exit_code == 0
    assert (tmp_path / ".agents" / "skills" / "agentflow" / "SKILL.md").is_file()
    # Earlier wrong paths must NOT be created
    assert not (tmp_path / ".agent").exists()
    assert not (tmp_path / ".codex").exists()


def test_install_github_writes_copilot_instructions_and_skill(
    cmd: SkillsCommand, tmp_path: Path
) -> None:
    exit_code = cmd.execute(agent="github", path=str(tmp_path))
    assert exit_code == 0

    instructions = tmp_path / ".github" / "instructions" / "agentflow.instructions.md"
    assert instructions.is_file()
    content = instructions.read_text(encoding="utf-8")
    # Copilot frontmatter required for the file to be picked up
    assert content.startswith("---\napplyTo:")

    skill_dir = tmp_path / ".github" / "skills" / "agentflow"
    assert (skill_dir / "SKILL.md").is_file()
    assert (skill_dir / "references").is_dir()

    manifest = json.loads((skill_dir / ".agentflow-skill.json").read_text(encoding="utf-8"))
    assert manifest["agent"] == "GitHub"
    assert manifest["cli_version"] == CLI_VERSION
    assert "installed_at" in manifest


def test_install_existing_dir_without_force_fails(
    cmd: SkillsCommand, out: _CapturingOutput, tmp_path: Path
) -> None:
    assert cmd.execute(agent="claude", path=str(tmp_path)) == 0
    out.errors.clear()
    exit_code = cmd.execute(agent="claude", path=str(tmp_path))
    assert exit_code != 0
    assert any("already installed" in e for e in out.errors)


def test_install_force_overwrites_existing(cmd: SkillsCommand, tmp_path: Path) -> None:
    skill_dir = tmp_path / ".claude" / "skills" / "agentflow"
    cmd.execute(agent="claude", path=str(tmp_path))
    # mutate the install so we can detect overwrite
    sentinel = skill_dir / "SENTINEL.txt"
    sentinel.write_text("user-local content", encoding="utf-8")

    exit_code = cmd.execute(agent="claude", path=str(tmp_path), force=True)
    assert exit_code == 0
    assert not sentinel.exists(), "force install should remove old contents"
    assert (skill_dir / "SKILL.md").is_file()


def test_force_overwrites_copilot_file(cmd: SkillsCommand, tmp_path: Path) -> None:
    instructions = tmp_path / ".github" / "instructions" / "agentflow.instructions.md"
    cmd.execute(agent="github", path=str(tmp_path))
    instructions.write_text("user-edited", encoding="utf-8")
    sentinel = tmp_path / ".github" / "skills" / "agentflow" / "SENTINEL.txt"
    sentinel.write_text("user-local content", encoding="utf-8")

    exit_code = cmd.execute(agent="github", path=str(tmp_path), force=True)
    assert exit_code == 0
    assert instructions.read_text(encoding="utf-8").startswith("---\napplyTo:")
    assert not sentinel.exists(), "force install should remove old GitHub skill contents"


# --- --all flow -----------------------------------------------------------


def test_all_installs_every_agent(cmd: SkillsCommand, tmp_path: Path) -> None:
    exit_code = cmd.execute(all_agents=True, path=str(tmp_path))
    assert exit_code == 0

    assert (tmp_path / ".agents" / "skills" / "agentflow" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "agentflow" / "SKILL.md").is_file()
    assert (tmp_path / ".github" / "instructions" / "agentflow.instructions.md").is_file()
    assert (tmp_path / ".github" / "skills" / "agentflow" / "SKILL.md").is_file()


def test_all_skips_existing_without_force(
    cmd: SkillsCommand, out: _CapturingOutput, tmp_path: Path
) -> None:
    cmd.execute(agent="claude", path=str(tmp_path))
    out.successes.clear()

    exit_code = cmd.execute(all_agents=True, path=str(tmp_path))
    assert exit_code == 0
    # Codex and GitHub were installed, Claude was skipped
    installed = " ".join(out.successes)
    assert "Codex" in installed
    assert "GitHub" in installed
    assert "Claude" not in installed
    assert any("Skipped existing" in w and "Claude" in w for w in out.warnings)


def test_all_with_force_reinstalls_everything(cmd: SkillsCommand, tmp_path: Path) -> None:
    cmd.execute(all_agents=True, path=str(tmp_path))
    sentinel = tmp_path / ".claude" / "skills" / "agentflow" / "SENTINEL.txt"
    sentinel.write_text("x", encoding="utf-8")

    exit_code = cmd.execute(all_agents=True, path=str(tmp_path), force=True)
    assert exit_code == 0
    assert not sentinel.exists()


# --- path safety ----------------------------------------------------------


def test_install_at_filesystem_root_is_refused(
    cmd: SkillsCommand, out: _CapturingOutput
) -> None:
    root = Path(Path.cwd().anchor) if Path.cwd().anchor else Path("/")
    exit_code = cmd.execute(agent="claude", path=str(root))
    assert exit_code != 0
    assert any("filesystem root" in e for e in out.errors)


def test_install_at_home_dir_is_refused(
    cmd: SkillsCommand, out: _CapturingOutput
) -> None:
    exit_code = cmd.execute(agent="claude", path=str(Path.home()))
    assert exit_code != 0
    assert any("home directory" in e for e in out.errors)


# --- non-interactive guard ------------------------------------------------


def test_no_agent_with_non_tty_stdin_errors(
    cmd: SkillsCommand, out: _CapturingOutput, tmp_path: Path
) -> None:
    with patch.object(sys.stdin, "isatty", return_value=False):
        exit_code = cmd.execute(path=str(tmp_path))
    assert exit_code != 0
    assert any("stdin is not interactive" in e for e in out.errors)
