"""Skill templates for coding agents (Claude Code, Cursor, Copilot, Windsurf, Codex).

The shared body lives in ``agentflow_skill.md`` so the rendered markdown can
remain well-formatted without fighting Python line-length rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final


_TEMPLATE_DIR: Final[Path] = Path(__file__).parent
_SKILL_BODY: Final[str] = (_TEMPLATE_DIR / "agentflow_skill.md").read_text(encoding="utf-8")


_CURSOR_FRONTMATTER: Final[str] = (
    "---\n"
    "description: AgentFlow framework conventions and golden-path snippets\n"
    "alwaysApply: true\n"
    "---\n\n"
)


# Registry mapping agent id -> (relative output path, file content).
SKILL_TARGETS: Final[dict[str, tuple[str, str]]] = {
    "claude": ("CLAUDE.md", _SKILL_BODY),
    "cursor": (".cursor/rules/agentflow.mdc", _CURSOR_FRONTMATTER + _SKILL_BODY),
    "copilot": (".github/copilot-instructions.md", _SKILL_BODY),
    "windsurf": (".windsurfrules", _SKILL_BODY),
    "codex": ("AGENTS.md", _SKILL_BODY),
}
