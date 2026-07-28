"""Safe interactive showcase for Agentflow terminal motion."""

from __future__ import annotations

import time
from typing import Any

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.exceptions import ValidationError


class DemoCommand(BaseCommand):
    """Preview command-specific animations without external side effects."""

    _STYLES = ("typing", "network", "init", "build", "eval")
    _ALIASES = {"play": "typing", "api": "network"}

    def execute(self, style: str = "all", **kwargs: Any) -> int:
        normalized = self._ALIASES.get(style.strip().lower(), style.strip().lower())
        if normalized != "all" and normalized not in self._STYLES:
            return self.handle_error(
                ValidationError(
                    f"Unknown animation style '{style}'. "
                    f"Choose all, {', '.join(self._STYLES)}.",
                    field="style",
                )
            )

        selected = self._STYLES if normalized == "all" else (normalized,)
        subtitles = {
            "typing": "Full-screen Agentflow identity and workspace transition",
            "network": "Live agent network and playground connection",
            "init": "Project scaffold assembly",
            "build": "Container delivery pipeline",
            "eval": "Evaluation scan and completion states",
        }
        command_names = {
            "typing": "typing",
            "network": "api",
            "init": "init",
            "build": "build",
            "eval": "eval",
        }
        for theme in selected:
            self.output.command_header(command_names[theme], subtitles[theme])

        stages = (
            ("Resolving graph topology", "Graph topology resolved", "aesthetic"),
            ("Assembling runtime pipeline", "Runtime pipeline assembled", "bouncingBar"),
            ("Connecting developer experience", "Developer experience connected", "moon"),
        )
        for message, done, spinner in stages:
            with self.output.activity(message, done=done, spinner=spinner):
                time.sleep(0.35)

        self.output.completion_screen(
            "Animation showcase",
            "All preview states rendered successfully",
            details={
                "Themes": ", ".join(selected),
                "Side effects": "none",
                "Fallback": "automatic for CI, pipes, and JSON",
            },
            next_steps=[
                "Run `agentflow play` to see the network theme in a real workflow.",
                "Use `agentflow --no-animation COMMAND` for static accessible output.",
            ],
        )
        return 0
