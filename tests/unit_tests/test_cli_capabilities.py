"""Terminal capability policy tests."""

from __future__ import annotations

import io

from tenxgraph_api.cli.capabilities import (
    ColorMode,
    OutputFormat,
    ProgressMode,
    TerminalCapabilities,
    cli_env_name,
)


class TTYStream(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_interactive_terminal_enables_human_animation(monkeypatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    capabilities = TerminalCapabilities.detect(stream=TTYStream())
    assert capabilities.interactive is True
    assert capabilities.output_format == OutputFormat.HUMAN
    assert capabilities.progress_mode == ProgressMode.TTY
    assert capabilities.animation is True


def test_pipe_automatically_uses_plain_output() -> None:
    capabilities = TerminalCapabilities.detect(stream=io.StringIO())
    assert capabilities.output_format == OutputFormat.PLAIN
    assert capabilities.progress_mode == ProgressMode.PLAIN
    assert capabilities.animation is False


def test_ci_disables_interactivity_and_animation(monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")
    capabilities = TerminalCapabilities.detect(stream=TTYStream())
    assert capabilities.is_ci is True
    assert capabilities.interactive is False
    assert capabilities.animation is False


def test_explicit_color_policy_wins(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    capabilities = TerminalCapabilities.detect(
        stream=io.StringIO(),
        color_mode=ColorMode.ALWAYS,
        output_format=OutputFormat.HUMAN,
    )
    assert capabilities.color is True


def test_structured_output_never_animates() -> None:
    capabilities = TerminalCapabilities.detect(
        stream=TTYStream(),
        output_format=OutputFormat.JSONL,
        progress_mode=ProgressMode.TTY,
    )
    assert capabilities.color is False
    assert capabilities.animation is False


def test_cli_env_name_prefers_tenxgraph_prefix(monkeypatch) -> None:
    monkeypatch.delenv("TENXGRAPH_NO_SPINNER", raising=False)
    monkeypatch.delenv("AGENTFLOW_NO_SPINNER", raising=False)
    assert cli_env_name("NO_SPINNER") == "TENXGRAPH_NO_SPINNER"

    monkeypatch.setenv("AGENTFLOW_NO_SPINNER", "1")
    assert cli_env_name("NO_SPINNER") == "AGENTFLOW_NO_SPINNER"

    monkeypatch.setenv("TENXGRAPH_NO_SPINNER", "0")
    assert cli_env_name("NO_SPINNER") == "TENXGRAPH_NO_SPINNER"
