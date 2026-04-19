"""Skill command — generate coding-agent skill files (CLAUDE.md, .cursorrules, ...)."""

from pathlib import Path
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import FileOperationError
from agentflow_cli.cli.templates.skills import SKILL_TARGETS


class SkillCommand(BaseCommand):
    """Write AgentFlow skill files for common coding agents."""

    def execute(
        self,
        path: str = ".",
        agent: str = "all",
        force: bool = False,
        **kwargs: Any,
    ) -> int:
        """Generate skill files.

        Args:
            path: Project directory to generate into.
            agent: Agent id to target. One of the keys in ``SKILL_TARGETS`` or ``"all"``.
            force: Overwrite existing files.
        """
        try:
            subtitle = (
                "Generate AgentFlow skill files for coding agents "
                "(Claude Code, Cursor, Copilot, Windsurf, Codex)"
            )
            self.output.print_banner("Skill", subtitle, color="cyan")

            base_path = Path(path)
            base_path.mkdir(parents=True, exist_ok=True)

            agent_key = agent.lower().strip()
            if agent_key == "all":
                targets = SKILL_TARGETS
            elif agent_key in SKILL_TARGETS:
                targets = {agent_key: SKILL_TARGETS[agent_key]}
            else:
                supported = ", ".join(sorted(["all", *SKILL_TARGETS]))
                raise FileOperationError(
                    f"Unknown agent '{agent}'. Supported: {supported}."
                )

            written: list[Path] = []
            for name, (rel_path, content) in targets.items():
                dest = base_path / rel_path
                self._write_file(dest, content, force=force)
                written.append(dest)
                self.output.success(f"[{name}] wrote {dest}")

            self.output.info("\n🚀 Next steps:")
            steps = [
                "Commit the generated files so your coding agent picks them up.",
                "Edit the content to capture any project-specific conventions.",
                "Re-run 'agentflow skill --force' whenever AgentFlow usage changes.",
            ]
            for i, step in enumerate(steps, 1):
                self.output.info(f"{i}. {step}")

            return 0

        except FileOperationError as e:
            return self.handle_error(e)
        except Exception as e:
            return self.handle_error(
                FileOperationError(f"Failed to generate skill files: {e}")
            )

    def _write_file(self, path: Path, content: str, *, force: bool) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            if path.exists() and not force:
                raise FileOperationError(
                    f"File already exists: {path}. Use --force to overwrite.",
                    file_path=str(path),
                )

            path.write_text(content, encoding="utf-8")
            self.logger.debug("Wrote skill file: %s", path)

        except OSError as e:
            raise FileOperationError(
                f"Failed to write file {path}: {e}", file_path=str(path)
            ) from e
