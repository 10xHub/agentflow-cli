"""Tests for the side-effect-free terminal animation showcase."""

from __future__ import annotations

import io

from agentflow_cli.cli.commands import demo as demo_module
from agentflow_cli.cli.commands.demo import DemoCommand
from agentflow_cli.cli.core.output import OutputFormatter


def test_demo_renders_all_themes_without_side_effects(monkeypatch) -> None:
    monkeypatch.setattr(demo_module.time, "sleep", lambda _seconds: None)
    stream = io.StringIO()
    command = DemoCommand(OutputFormatter(stream=stream))

    assert command.execute() == 0
    rendered = stream.getvalue()
    for theme in ("Typing", "Api", "Init", "Build", "Eval"):
        assert theme in rendered
    assert "All preview states rendered successfully" in rendered
    assert "none" in rendered


def test_demo_rejects_unknown_style() -> None:
    stream = io.StringIO()
    command = DemoCommand(OutputFormatter(stream=stream))

    assert command.execute(style="unknown") != 0
    assert "Unknown animation style" in stream.getvalue()


def test_play_alias_selects_typing_theme(monkeypatch) -> None:
    monkeypatch.setattr(demo_module.time, "sleep", lambda _seconds: None)
    stream = io.StringIO()
    command = DemoCommand(OutputFormatter(stream=stream))

    assert command.execute(style="play") == 0
    assert "Typing" in stream.getvalue()
