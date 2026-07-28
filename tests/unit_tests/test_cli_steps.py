"""Tests for step timelines and determinate progress runs."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from agentflow_cli.cli.core.steps import (
    LiveProgressRun,
    LiveTimeline,
    QuietTimeline,
    StaticProgressRun,
    StaticTimeline,
    StepState,
    StructuredProgressRun,
    StructuredTimeline,
    format_elapsed,
)
from agentflow_cli.cli.core.theme import UNICODE_GLYPHS


STEPS = (("one", "First stage"), ("two", "Second stage"))


def static(emitted: list[str]) -> StaticTimeline:
    return StaticTimeline(
        glyphs=UNICODE_GLYPHS,
        emit=emitted.append,
        title="Doing work",
        steps=STEPS,
    )


def test_format_elapsed_switches_to_minutes() -> None:
    assert format_elapsed(0.04) == "0.0s"
    assert format_elapsed(12.34) == "12.3s"
    assert format_elapsed(63.0) == "1m 03s"
    assert format_elapsed(3600.0) == "60m 00s"


def test_static_timeline_reports_each_transition() -> None:
    emitted: list[str] = []
    with static(emitted) as timeline:
        with timeline.step("one") as step:
            step.detail("resolved config")
        with timeline.step("two"):
            pass

    assert emitted[0].endswith("Doing work")
    assert any("First stage" in line and "resolved config" in line for line in emitted)
    assert sum(line.startswith(UNICODE_GLYPHS.check) for line in emitted) == 2


def test_timeline_marks_a_raising_step_as_failed_and_reraises() -> None:
    emitted: list[str] = []
    timeline = static(emitted)
    with pytest.raises(RuntimeError, match="boom"), timeline:
        with timeline.step("one"):
            raise RuntimeError("boom")

    assert timeline.failed is True
    assert any(line.startswith(UNICODE_GLYPHS.cross) for line in emitted)


def test_skipped_step_is_neither_done_nor_failed() -> None:
    emitted: list[str] = []
    timeline = static(emitted)
    with timeline, timeline.step("one") as step:
        step.skip("nothing to do")

    assert timeline._index["one"].state is StepState.SKIPPED
    assert timeline.failed is False
    assert any("nothing to do" in line for line in emitted)


def test_timeline_accepts_stages_discovered_at_runtime() -> None:
    emitted: list[str] = []
    timeline = static(emitted)
    with timeline:
        timeline.add("three", "Third stage")
        with timeline.step("three"):
            pass
        # An unknown key still runs rather than raising, so a command can
        # report work it only learned about mid-flight.
        with timeline.step("four", "Fourth stage"):
            pass

    assert [step.key for step in timeline._steps] == ["one", "two", "three", "four"]
    assert any("Fourth stage" in line for line in emitted)


def test_structured_timeline_emits_versioned_lifecycle_events() -> None:
    events: list[tuple[str, str, dict]] = []
    timeline = StructuredTimeline(
        emit=lambda event, message, data: events.append((event, message, data)),
        title="Doing work",
        steps=STEPS,
    )
    with timeline, timeline.step("one") as step:
        step.detail("resolved config")

    names = [event for event, _, _ in events]
    assert names == ["timeline_start", "step_start", "step_end", "timeline_end"]
    assert events[2][2]["status"] == "done"
    assert events[2][2]["detail"] == "resolved config"
    assert events[-1][2]["status"] == "completed"


def test_structured_timeline_reports_failure_status() -> None:
    events: list[tuple[str, str, dict]] = []
    timeline = StructuredTimeline(
        emit=lambda event, message, data: events.append((event, message, data)),
        steps=STEPS,
    )
    with pytest.raises(ValueError, match="nope"), timeline:
        with timeline.step("one"):
            raise ValueError("nope")

    assert events[-1][2]["status"] == "failed"


def test_quiet_timeline_produces_no_output_but_still_runs_work() -> None:
    ran = []
    timeline = QuietTimeline(STEPS)
    with timeline, timeline.step("one"):
        ran.append("worked")
    assert ran == ["worked"]


def test_live_timeline_leaves_its_final_state_in_the_buffer() -> None:
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=True, width=100, legacy_windows=False)
    timeline = LiveTimeline(
        console,
        glyphs=UNICODE_GLYPHS,
        title="Doing work",
        steps=STEPS,
    )
    with timeline:
        with timeline.step("one") as step:
            step.detail("resolved config")
        with timeline.step("two"):
            pass

    rendered = stream.getvalue()
    assert "First stage" in rendered
    assert "Second stage" in rendered
    assert "resolved config" in rendered


def test_progress_run_tracks_a_pass_fail_tally() -> None:
    emitted: list[str] = []
    run = StaticProgressRun(
        total=3,
        title="Running cases",
        glyphs=UNICODE_GLYPHS,
        emit=emitted.append,
    )
    with run:
        run.record("a", status="passed")
        run.record("b", status="failed", detail="0.4s")
        run.record("c", status="passed")

    assert run.completed == 3
    assert run.tally == {"passed": 2, "failed": 1, "error": 0, "skipped": 0}
    assert "[  2/3]" in emitted[2]
    assert "FAILED" in emitted[2]


def test_structured_progress_run_emits_one_event_per_item() -> None:
    events: list[tuple[str, str, dict]] = []
    run = StructuredProgressRun(
        total=2,
        title="Running cases",
        emit=lambda event, message, data: events.append((event, message, data)),
    )
    with run:
        run.record("a", status="passed")
        run.record("b", status="error")

    assert [event for event, _, _ in events] == [
        "progress_start",
        "progress",
        "progress",
        "progress_end",
    ]
    assert events[1][2]["completed"] == 1
    assert events[-1][2]["error"] == 1


def test_live_progress_run_renders_results_above_its_bar() -> None:
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=True, width=100, legacy_windows=False)
    with LiveProgressRun(console, total=2, title="Running cases", glyphs=UNICODE_GLYPHS) as run:
        run.record("weather::tokyo", status="passed", detail="0.4s")
        run.record("weather::oslo", status="failed", detail="0.5s")

    rendered = stream.getvalue()
    assert "weather::tokyo" in rendered
    assert "weather::oslo" in rendered
    assert run.tally["failed"] == 1
