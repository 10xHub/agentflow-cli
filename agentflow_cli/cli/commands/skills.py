"""Skills command implementation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import typer

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import FileOperationError, ValidationError


class SkillsCommand(BaseCommand):
    """Command to install bundled Agentflow skills for supported agents."""

    _AGENTS: dict[str, tuple[str, str]] = {
        "1": ("Codex", ".agent/skills/agentflow"),
        "codex": ("Codex", ".agent/skills/agentflow"),
        "2": ("Claude", ".claude/skills/agentflow"),
        "claude": ("Claude", ".claude/skills/agentflow"),
        "3": ("Github", ".github/skills/agentflow"),
        "github": ("Github", ".github/skills/agentflow"),
    }

    def execute(
        self,
        agent: str | None = None,
        path: str = ".",
        force: bool = False,
        **kwargs: Any,
    ) -> int:
        """Execute the skills command.

        Args:
            agent: Target agent name or menu number.
            path: Project directory where the agent skill directory should be created.
            force: Overwrite existing skill directory.
            **kwargs: Additional arguments.

        Returns:
            Exit code.
        """
        try:
            self.output.print_banner(
                "Skills",
                "Install bundled Agentflow skills for Codex, Claude, or Github.",
                color="magenta",
            )

            agent_name, relative_target = self._select_agent(agent)
            source = self._source_dir()
            target = Path(path).resolve() / relative_target

            if not source.is_dir():
                raise FileOperationError(
                    f"Bundled skills template not found: {source}", file_path=str(source)
                )

            if target.exists():
                if not force:
                    raise FileOperationError(
                        f"Skill directory already exists: {target}. Use --force to overwrite.",
                        file_path=str(target),
                    )
                shutil.rmtree(target)

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )

            self.output.success(f"Installed Agentflow skills for {agent_name} at {target}")
            return 0

        except (FileOperationError, ValidationError) as e:
            return self.handle_error(e)
        except Exception as e:
            file_error = FileOperationError(f"Failed to install Agentflow skills: {e}")
            return self.handle_error(file_error)

    def _select_agent(self, agent: str | None) -> tuple[str, str]:
        if agent:
            return self._normalize_agent(agent)

        self.output.print_list(
            [
                "1. Codex",
                "2. Claude",
                "3. Github",
            ],
            title="Which agent?",
            bullet="-",
        )
        selected = typer.prompt("Select an agent", default="1")
        return self._normalize_agent(selected)

    def _normalize_agent(self, value: str) -> tuple[str, str]:
        key = value.strip().lower()
        if key in self._AGENTS:
            return self._AGENTS[key]

        valid = "Codex, Claude, Github, or 1, 2, 3"
        raise ValidationError(f"Invalid agent '{value}'. Choose {valid}.", field="agent")

    def _source_dir(self) -> Path:
        cli_dir = Path(__file__).resolve().parents[1]
        return cli_dir / "templates" / "skills" / "agent-skills"
