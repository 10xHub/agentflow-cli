"""Dummy thread-name generator — deterministic, no LLM."""

from __future__ import annotations

from agentflow_cli import ThreadNameGenerator


class MyNameGenerator(ThreadNameGenerator):
    """Derive a short thread title from the first user message (no LLM)."""

    MAX_TITLE_LEN = 50

    async def generate_name(self, messages: list[str]) -> str:
        first = next((m for m in messages if m and m.strip()), "")
        first = " ".join(first.split())
        if not first:
            return "new-conversation"
        return first[: self.MAX_TITLE_LEN] + ("…" if len(first) > self.MAX_TITLE_LEN else "")
