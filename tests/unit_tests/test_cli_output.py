"""Behavioral tests for adaptive CLI output."""

from __future__ import annotations

import io
import json
import sys

from agentflow_cli.cli.capabilities import ColorMode, OutputFormat, ProgressMode
from agentflow_cli.cli.core.output import (
    OutputFormatter,
    emphasize,
    error,
    info,
    output,
    print_banner,
    success,
    warning,
)


def formatter(**kwargs) -> tuple[OutputFormatter, io.StringIO]:
    stream = io.StringIO()
    return OutputFormatter(stream=stream, **kwargs), stream


def test_initialization_default_and_custom_stream() -> None:
    assert OutputFormatter().stream == sys.stdout
    custom = io.StringIO()
    assert OutputFormatter(stream=custom).stream is custom


def test_plain_banner_contains_title_and_subtitle() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN)
    rendered.print_banner("Test Title", "Test Subtitle", width=100)
    value = stream.getvalue()
    assert "== Test Title ==" in value
    assert "Test Subtitle" in value


def test_semantic_messages_render_visible_text_and_symbols() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN)
    rendered.success("Operation successful")
    rendered.error("An error occurred")
    rendered.info("Information message")
    rendered.warning("Warning message")
    rendered.emphasize("Important message")
    value = stream.getvalue()
    for expected in (
        "Operation successful",
        "An error occurred",
        "Information message",
        "Warning message",
        "Important message",
    ):
        assert expected in value


def test_messages_can_omit_symbols() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN)
    rendered.success("success", emoji=False)
    rendered.error("error", emoji=False)
    rendered.info("info", emoji=False)
    rendered.warning("warning", emoji=False)
    assert stream.getvalue().splitlines() == ["success", "error", "info", "warning"]


def test_list_key_values_and_table_render_content() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN)
    rendered.print_list(["one", "two"], title="Items", bullet="-")
    rendered.print_key_value_pairs({"name": "Ada", "age": 30}, title="Person", indent=4)
    rendered.print_table(
        ["Name", "Age", "City"],
        [["Ada", "30"], ["Grace", "28", "New York", "ignored"]],
        title="People",
    )
    value = stream.getvalue()
    for expected in ("Items", "one", "two", "Person", "Ada", "30", "People", "New York"):
        assert expected in value


def test_empty_list_and_table_do_not_fail() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN)
    rendered.print_list([])
    rendered.print_table(["Name"], [])
    assert "Name" in stream.getvalue()


def test_jsonl_messages_are_versioned_objects() -> None:
    rendered, stream = formatter(output_format=OutputFormat.JSONL)
    rendered.success("done")
    rendered.print_table(["name"], [["agent"]], title="Agents")
    payloads = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert payloads[0] == {
        "schema": "agentflow.cli/v1",
        "type": "success",
        "message": "done",
    }
    assert payloads[1]["type"] == "table"
    assert payloads[1]["rows"] == [{"name": "agent"}]


def test_quiet_suppresses_non_error_output() -> None:
    rendered, stream = formatter(output_format=OutputFormat.PLAIN, quiet=True)
    rendered.print_banner("hidden")
    rendered.success("hidden")
    rendered.info("hidden")
    rendered.warning("hidden")
    rendered.print_list(["hidden"])
    rendered.error("visible", emoji=False)
    assert stream.getvalue() == "visible\n"


def test_no_color_produces_no_ansi_sequences() -> None:
    rendered, stream = formatter(
        output_format=OutputFormat.HUMAN,
        color_mode=ColorMode.NEVER,
    )
    rendered.success("done")
    assert "\x1b[" not in stream.getvalue()


def test_plain_status_degrades_to_a_checkpoint() -> None:
    rendered, stream = formatter(
        output_format=OutputFormat.PLAIN,
        progress_mode=ProgressMode.PLAIN,
    )
    with rendered.status("Loading"):
        pass
    assert "Loading" in stream.getvalue()


def test_plain_command_header_degrades_to_static_banner() -> None:
    rendered, stream = formatter(
        output_format=OutputFormat.PLAIN,
        progress_mode=ProgressMode.PLAIN,
    )
    rendered.command_header("play", "Start the playground")
    assert "== Play ==" in stream.getvalue()
    assert "Start the playground" in stream.getvalue()


def test_forced_tty_header_uses_animation_renderer(monkeypatch) -> None:
    class TTYStream(io.StringIO):
        def isatty(self) -> bool:
            return True

    calls: list[tuple[str, str | None, bool, bool]] = []
    monkeypatch.setattr(
        "agentflow_cli.cli.core.output.render_command_intro",
        lambda _console, *, command, subtitle, unicode, persistent_screen: calls.append(
            (command, subtitle, unicode, persistent_screen)
        ),
    )
    stream = TTYStream()
    rendered = OutputFormatter(
        stream=stream,
        output_format=OutputFormat.HUMAN,
        progress_mode=ProgressMode.TTY,
    )
    rendered.command_header("play", "Start the playground")
    assert calls == [("play", "Start the playground", True, False)]


def test_fullscreen_session_owns_and_restores_alternate_screen(monkeypatch) -> None:
    class FakeScreen:
        entered = False
        exited = False

        def __enter__(self):
            self.entered = True
            return self

        def __exit__(self, *_args):
            self.exited = True

    class FakeConsole:
        def __init__(self) -> None:
            self.context = FakeScreen()

        def screen(self, **_kwargs):
            return self.context

    rendered, _stream = formatter(progress_mode=ProgressMode.TTY)
    console = FakeConsole()
    monkeypatch.setattr(rendered, "_console", lambda **_kwargs: console)

    assert rendered.start_fullscreen_session() is True
    assert rendered.fullscreen_active is True
    assert console.context.entered is True
    assert rendered.start_fullscreen_session() is False

    rendered.end_fullscreen_session()
    assert rendered.fullscreen_active is False
    assert console.context.exited is True


def test_structured_activity_emits_lifecycle_events() -> None:
    rendered, stream = formatter(output_format=OutputFormat.JSONL)
    with rendered.activity("Loading graph", done="Graph loaded"):
        pass
    payloads = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [payload["type"] for payload in payloads] == [
        "progress_start",
        "progress_end",
        "success",
    ]
    assert payloads[1]["status"] == "completed"


def test_structured_completion_screen_is_one_event() -> None:
    rendered, stream = formatter(output_format=OutputFormat.JSONL)
    rendered.completion_screen(
        "Ready",
        "Server configured",
        details={"API": "http://localhost:8000"},
        next_steps=["Open docs"],
    )
    payload = json.loads(stream.getvalue())
    assert payload["type"] == "completion"
    assert payload["title"] == "Ready"
    assert payload["details"]["API"] == "http://localhost:8000"


def test_global_convenience_functions_delegate(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(output, "print_banner", lambda value, *a, **k: calls.append(("banner", value)))
    monkeypatch.setattr(output, "success", lambda value, *a, **k: calls.append(("success", value)))
    monkeypatch.setattr(output, "error", lambda value, *a, **k: calls.append(("error", value)))
    monkeypatch.setattr(output, "info", lambda value, *a, **k: calls.append(("info", value)))
    monkeypatch.setattr(output, "warning", lambda value, *a, **k: calls.append(("warning", value)))
    monkeypatch.setattr(output, "emphasize", lambda value: calls.append(("emphasize", value)))

    print_banner("a")
    success("b")
    error("c")
    info("d")
    warning("e")
    emphasize("f")

    assert calls == [
        ("banner", "a"),
        ("success", "b"),
        ("error", "c"),
        ("info", "d"),
        ("warning", "e"),
        ("emphasize", "f"),
    ]


def test_global_instance_exists() -> None:
    assert isinstance(output, OutputFormatter)
