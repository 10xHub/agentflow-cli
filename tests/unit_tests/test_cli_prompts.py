"""Tests for the shared guided-prompt service."""

from __future__ import annotations

import pytest
import questionary
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

import agentflow_cli.cli.core.prompts as prompts_module
from agentflow_cli.cli.core.prompts import (
    MULTI_SELECT_HINT,
    PROMPT_STYLE,
    Choice,
    PromptService,
)
from agentflow_cli.cli.exceptions import ValidationError


class _StubQuestion:
    """Stands in for a questionary Question without touching the terminal."""

    def __init__(self, answer: object = None, raises: Exception | None = None) -> None:
        self.answer = answer
        self.raises = raises

    def ask(self) -> object:
        if self.raises is not None:
            raise self.raises
        return self.answer


# --- choice rendering -----------------------------------------------------


def test_choice_keeps_description_visually_secondary() -> None:
    rendered = Choice("codex", "Codex", ".agents/skills/agentflow").to_questionary()
    assert rendered.value == "codex"
    assert rendered.title == [
        ("class:text", "Codex"),
        ("class:instruction", "  .agents/skills/agentflow"),
    ]


def test_choice_without_description_is_title_only() -> None:
    rendered = Choice("codex", "Codex").to_questionary()
    assert rendered.title == [("class:text", "Codex")]


def test_choice_carries_checked_and_disabled_state() -> None:
    rendered = Choice("x", "X", checked=True, disabled="not supported here").to_questionary()
    assert rendered.checked is True
    assert rendered.disabled == "not supported here"


# --- interactivity policy -------------------------------------------------


def test_require_interactive_passes_when_a_user_is_present() -> None:
    PromptService(interactive=True).require_interactive(field="agent", alternatives="Pass --agent.")


def test_require_interactive_explains_the_flag_alternative() -> None:
    service = PromptService(interactive=False)
    with pytest.raises(ValidationError) as excinfo:
        service.require_interactive(field="agent", alternatives="Pass --agent codex.")

    message = str(excinfo.value)
    assert "stdin is not interactive" in message
    assert "Pass --agent codex." in message


# --- chrome restoration ---------------------------------------------------


def test_pinned_chrome_is_restored_after_every_answer(monkeypatch) -> None:
    """Prompt-toolkit erases past a scrolling region, taking the footer with it."""
    redraws: list[int] = []
    service = PromptService(interactive=True, on_answered=lambda: redraws.append(1))
    monkeypatch.setattr(questionary, "confirm", lambda *a, **k: _StubQuestion(True))

    assert service.confirm("Overwrite?") is True
    assert redraws == [1]


def test_pinned_chrome_is_restored_even_when_a_prompt_raises(monkeypatch) -> None:
    redraws: list[int] = []
    service = PromptService(interactive=True, on_answered=lambda: redraws.append(1))
    monkeypatch.setattr(
        questionary,
        "text",
        lambda *a, **k: _StubQuestion(raises=RuntimeError("terminal lost")),
    )

    with pytest.raises(ValidationError):
        service.text("Name?")
    assert redraws == [1]


def test_cancelling_a_prompt_returns_none(monkeypatch) -> None:
    service = PromptService(interactive=True)
    monkeypatch.setattr(questionary, "select", lambda *a, **k: _StubQuestion(None))
    assert service.select("Pick", [Choice("a", "A")]) is None


# --- terminals that cannot host a prompt ----------------------------------


def test_a_tty_that_cannot_host_a_prompt_counts_as_non_interactive(monkeypatch) -> None:
    """MSYS/Cygwin stdin reports as a TTY but prompt-toolkit cannot attach."""
    monkeypatch.setattr(prompts_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(prompts_module, "prompt_toolkit_available", lambda: False)
    assert PromptService().interactive is False


def test_a_usable_tty_is_interactive(monkeypatch) -> None:
    monkeypatch.setattr(prompts_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(prompts_module, "prompt_toolkit_available", lambda: True)
    assert PromptService().interactive is True


def test_availability_probe_reports_false_when_the_console_is_rejected(monkeypatch) -> None:
    import prompt_toolkit.output.defaults as pt_output

    def refuse() -> None:
        raise RuntimeError("Found xterm-256color, while expecting a Windows console.")

    monkeypatch.setattr(pt_output, "create_output", refuse)
    assert prompts_module.prompt_toolkit_available() is False


def test_a_terminal_failure_mid_prompt_is_a_usage_error_not_a_crash(monkeypatch) -> None:
    """It must not surface as AF-INTERNAL-001; the user needs an actionable fix."""
    service = PromptService(interactive=True)
    monkeypatch.setattr(
        questionary,
        "checkbox",
        lambda *a, **k: _StubQuestion(raises=RuntimeError("no console")),
    )

    with pytest.raises(ValidationError) as excinfo:
        service.checkbox("Which agents?", [Choice("a", "A")])
    assert "command-line flag" in str(excinfo.value)


# --- what the service hands to questionary --------------------------------


def test_checkbox_ships_the_toggle_hint_and_shared_style(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def capture(message, **kwargs):
        captured.update(kwargs, message=message)
        return _StubQuestion(["a"])

    monkeypatch.setattr(questionary, "checkbox", capture)
    service = PromptService(interactive=True)
    assert service.checkbox("Which agents?", [Choice("a", "A")]) == ["a"]

    assert captured["message"] == "Which agents?"
    assert captured["instruction"] == MULTI_SELECT_HINT
    assert captured["style"] is PROMPT_STYLE


def test_select_resolves_the_default_to_a_real_choice(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def capture(message, **kwargs):
        captured.update(kwargs)
        return _StubQuestion("b")

    monkeypatch.setattr(questionary, "select", capture)
    service = PromptService(interactive=True)
    service.select("Pick", [Choice("a", "A"), Choice("b", "B")], default="b")

    assert captured["default"].value == "b"


def test_select_tolerates_a_default_that_is_not_offered(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def capture(message, **kwargs):
        captured.update(kwargs)
        return _StubQuestion("a")

    monkeypatch.setattr(questionary, "select", capture)
    PromptService(interactive=True).select("Pick", [Choice("a", "A")], default="missing")

    # Questionary rejects a default that is not among the choices, so an unknown
    # one must degrade to "no default" rather than blow up mid-prompt.
    assert captured["default"] is None


# --- end-to-end keystrokes ------------------------------------------------


def test_checkbox_choices_toggle_with_the_space_bar() -> None:
    """The interaction the CLI advertises: space toggles, enter confirms."""
    choices = [
        Choice("Codex", "Codex", ".agents/skills/agentflow"),
        Choice("Claude", "Claude", ".claude/skills/agentflow", checked=True),
        Choice("GitHub", "GitHub", ".github/skills/agentflow"),
    ]
    with create_pipe_input() as pipe:
        # space (toggle Codex on) · down · down · space (toggle GitHub on) · enter
        pipe.send_text(" \x1b[B\x1b[B \r")
        answer = questionary.checkbox(
            "Which agents?",
            choices=[choice.to_questionary() for choice in choices],
            style=PROMPT_STYLE,
            input=pipe,
            output=DummyOutput(),
        ).unsafe_ask()

    assert answer == ["Codex", "Claude", "GitHub"]


def test_prechecked_choices_come_back_without_any_keystrokes() -> None:
    choices = [
        Choice("Codex", "Codex", checked=False),
        Choice("Claude", "Claude", checked=True),
    ]
    with create_pipe_input() as pipe:
        pipe.send_text("\r")
        answer = questionary.checkbox(
            "Which agents?",
            choices=[choice.to_questionary() for choice in choices],
            style=PROMPT_STYLE,
            input=pipe,
            output=DummyOutput(),
        ).unsafe_ask()

    assert answer == ["Claude"]
