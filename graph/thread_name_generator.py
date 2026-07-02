"""Dummy thread-name generator — deterministic, no LLM."""

from __future__ import annotations

from agentflow_cli import ThreadNameGenerator


class MyNameGenerator(ThreadNameGenerator):
    """Derive a short thread title from the first user message (no LLM)."""

    async def generate_name(self, messages: list[str]) -> str:
        first = next((m for m in messages if m and m.strip()), "")
        first = " ".join(first.split())
        if not first:
            return "new-conversation"
        return first[:50] + ("…" if len(first) > 50 else "")
