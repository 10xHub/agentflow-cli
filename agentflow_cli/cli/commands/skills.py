"""Skills command implementation."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import typer

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import CLI_VERSION
from agentflow_cli.cli.exceptions import FileOperationError, ValidationError


_MANIFEST_FILENAME = ".agentflow-skill.json"


@dataclass(frozen=True)
class _InstallArtifact:
    """Describes one file or folder installed for an agent."""

    kind: Literal["folder", "file"]
    install_relpath: str
    source_relpath: str
    manifest: bool = False


@dataclass(frozen=True)
class _AgentTarget:
    """Describes how the bundled skill is materialised for one agent."""

    name: str
    artifacts: tuple[_InstallArtifact, ...]

    @property
    def kind(self) -> str:
        kinds = {artifact.kind for artifact in self.artifacts}
        if len(kinds) == 1:
            return next(iter(kinds))
        return "file+folder"


_TARGETS: tuple[_AgentTarget, ...] = (
    _AgentTarget(
        name="Codex",
        artifacts=(
            _InstallArtifact(
                kind="folder",
                install_relpath=".agents/skills/agentflow",
                source_relpath="agent-skills",
                manifest=True,
            ),
        ),
    ),
    _AgentTarget(
        name="Claude",
        artifacts=(
            _InstallArtifact(
                kind="folder",
                install_relpath=".claude/skills/agentflow",
                source_relpath="agent-skills",
                manifest=True,
            ),
        ),
    ),
    _AgentTarget(
        name="GitHub",
        artifacts=(
            _InstallArtifact(
                kind="file",
                install_relpath=".github/instructions/agentflow.instructions.md",
                source_relpath="copilot/agentflow.instructions.md",
            ),
            _InstallArtifact(
                kind="folder",
                install_relpath=".github/skills/agentflow",
                source_relpath="agent-skills",
                manifest=True,
            ),
        ),
    ),
)

_AGENT_LOOKUP: dict[str, _AgentTarget] = {
    **{t.name.lower(): t for t in _TARGETS},
    "1": _TARGETS[0],
    "2": _TARGETS[1],
    "3": _TARGETS[2],
}


class SkillsCommand(BaseCommand):
    """Command to install bundled Agentflow skills for supported agents."""

    def execute(
        self,
        agent: str | None = None,
        path: str = ".",
        force: bool = False,
        all_agents: bool = False,
        list_agents: bool = False,
        **kwargs: Any,
    ) -> int:
        """Execute the skills command.

        Args:
            agent: Target agent name or menu number.
            path: Project directory where the agent skill should be installed.
            force: Overwrite an existing installation.
            all_agents: Install for every supported agent.
            list_agents: Print supported agents and exit.
            **kwargs: Additional arguments.

        Returns:
            Exit code.
        """
        try:
            self.output.print_banner(
                "Skills",
                "Install bundled Agentflow skills for Codex, Claude, or GitHub Copilot.",
                color="magenta",
            )

            if list_agents:
                self._print_agents()
                return 0

            if all_agents and agent:
                raise ValidationError("--all cannot be combined with --agent.", field="agent")

            templates_root = self._templates_root()
            project_root = self._safe_project_root(path)

            if all_agents:
                return self._install_all(templates_root, project_root, force=force)

            target = self._select_agent(agent)
            self._install_one(templates_root, project_root, target, force=force)
            return 0

        except (FileOperationError, ValidationError) as e:
            return self.handle_error(e)
        except OSError as e:
            file_error = FileOperationError(f"Failed to install Agentflow skills: {e}")
            file_error.__cause__ = e
            return self.handle_error(file_error)

    def _install_one(
        self,
        templates_root: Path,
        project_root: Path,
        target: _AgentTarget,
        *,
        force: bool,
    ) -> None:
        installs = [
            (
                artifact,
                templates_root / artifact.source_relpath,
                project_root / artifact.install_relpath,
            )
            for artifact in target.artifacts
        ]
        for _artifact, source, _dest in installs:
            if not source.exists():
                raise FileOperationError(
                    f"Bundled skills template not found: {source}", file_path=str(source)
                )

        existing = [dest for _artifact, _source, dest in installs if dest.exists()]
        if existing and not force:
            paths = ", ".join(str(dest) for dest in existing)
            raise FileOperationError(
                f"Skill already installed at {paths}. Use --force to overwrite.",
                file_path=str(existing[0]),
            )

        for _artifact, _source, dest in installs:
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()

        installed_paths: list[str] = []
        for artifact, source, dest in installs:
            dest.parent.mkdir(parents=True, exist_ok=True)

            if artifact.kind == "folder":
                shutil.copytree(
                    source,
                    dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
                )
                if artifact.manifest:
                    self._write_manifest(dest, target.name)
            else:
                shutil.copyfile(source, dest)
            installed_paths.append(str(dest))

        self.output.success(
            f"Installed Agentflow skills for {target.name} at {', '.join(installed_paths)}"
        )

    def _install_all(self, templates_root: Path, project_root: Path, *, force: bool) -> int:
        installed = 0
        skipped: list[str] = []
        failed: list[str] = []
        for target in _TARGETS:
            existing = [
                project_root / artifact.install_relpath
                for artifact in target.artifacts
                if (project_root / artifact.install_relpath).exists()
            ]
            if existing and not force:
                paths = ", ".join(str(dest) for dest in existing)
                skipped.append(f"{target.name} ({paths})")
                continue
            try:
                self._install_one(templates_root, project_root, target, force=force)
                installed += 1
            except (FileOperationError, OSError, UnicodeError) as e:
                self.logger.error("Install failed for %s: %s", target.name, e)
                failed.append(f"{target.name}: {e}")

        if skipped:
            self.output.warning(
                "Skipped existing installs (use --force to overwrite): " + ", ".join(skipped)
            )
        if failed:
            self.output.error("Failed installs: " + "; ".join(failed))

        if failed and installed == 0:
            return 1
        return 0

    def _write_manifest(self, target_dir: Path, agent_name: str) -> None:
        manifest = {
            "agent": agent_name,
            "cli_version": CLI_VERSION,
            "installed_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        (target_dir / _MANIFEST_FILENAME).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    def _print_agents(self) -> None:
        rows = [
            [t.name, t.kind, ", ".join(a.install_relpath for a in t.artifacts)] for t in _TARGETS
        ]
        self.output.print_table(
            ["Agent", "Kind", "Install path (relative to --path)"],
            rows,
            title="Supported agents",
        )

    def _safe_project_root(self, path: str) -> Path:
        project_root = Path(path).resolve()
        if project_root.parent == project_root:
            raise ValidationError(
                f"Refusing to install skills at filesystem root: {project_root}",
                field="path",
            )
        if project_root == Path.home().resolve():
            raise ValidationError(
                f"Refusing to install skills directly into the home directory: {project_root}. "
                "Pass --path pointing at a project directory.",
                field="path",
            )
        return project_root

    def _select_agent(self, agent: str | None) -> _AgentTarget:
        if agent:
            return self._normalize_agent(agent)

        if not sys.stdin.isatty():
            raise ValidationError(
                "No --agent provided and stdin is not interactive. "
                "Pass --agent codex|claude|github or --all.",
                field="agent",
            )

        self.output.print_list(
            [f"{i}. {t.name}" for i, t in enumerate(_TARGETS, 1)],
            title="Which agent?",
            bullet="-",
        )
        selected = typer.prompt("Select an agent", default="1")
        return self._normalize_agent(selected)

    def _normalize_agent(self, value: str) -> _AgentTarget:
        key = value.strip().lower()
        if key in _AGENT_LOOKUP:
            return _AGENT_LOOKUP[key]

        valid = "Codex, Claude, GitHub, or 1, 2, 3"
        raise ValidationError(f"Invalid agent '{value}'. Choose {valid}.", field="agent")

    def _templates_root(self) -> Path:
        cli_dir = Path(__file__).resolve().parents[1]
        return cli_dir / "templates" / "skills"
