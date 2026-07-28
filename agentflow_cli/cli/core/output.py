"""Adaptive terminal output utilities for the CLI."""

from __future__ import annotations

import contextlib
import json
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, TextIO

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from agentflow_cli.cli.capabilities import (
    ColorMode,
    OutputFormat,
    ProgressMode,
    TerminalCapabilities,
)
from agentflow_cli.cli.constants import CLI_VERSION
from agentflow_cli.cli.core.animations import render_command_intro, render_session_header
from agentflow_cli.cli.core.steps import (
    LiveProgressRun,
    LiveTimeline,
    ProgressRun,
    QuietProgressRun,
    QuietTimeline,
    StaticProgressRun,
    StaticTimeline,
    StructuredProgressRun,
    StructuredTimeline,
    Timeline,
)
from agentflow_cli.cli.core.theme import (
    AGENTFLOW_THEME,
    Glyphs,
    glyphs_for,
    gradient_rule,
    gradient_text,
)


# Paint the alternate buffer before anything renders into it, so opt-in
# full-screen mode reads as a dedicated surface rather than a cleared prompt.
_FULLSCREEN_PAINT = "\x1b[48;2;11;11;18m\x1b[2J\x1b[H"
_FULLSCREEN_RESET = "\x1b[0m"


class OutputFormatter:
    """Render semantic CLI output for terminals, pipes, and automation."""

    def __init__(
        self,
        stream: TextIO | None = None,
        *,
        error_stream: TextIO | None = None,
        output_format: OutputFormat = OutputFormat.HUMAN,
        color_mode: ColorMode = ColorMode.AUTO,
        progress_mode: ProgressMode = ProgressMode.AUTO,
        quiet: bool = False,
    ) -> None:
        self._stream = stream
        self._error_stream = error_stream
        self.output_format = output_format
        self.color_mode = color_mode
        self.progress_mode = progress_mode
        self.quiet = quiet
        self._session_console: Console | None = None
        self._screen_active: bool = False
        self._consoles: dict[bool, Console] = {}
        self.capabilities = TerminalCapabilities.detect(
            stream=self.stream,
            output_format=output_format,
            color_mode=color_mode,
            progress_mode=progress_mode,
        )

    @property
    def stream(self) -> TextIO:
        """Current stdout stream, remaining compatible with CliRunner capture."""
        return self._stream or sys.stdout

    @property
    def error_stream(self) -> TextIO:
        """Current stderr stream, or the explicit test stream when supplied."""
        if self._error_stream is not None:
            return self._error_stream
        if self._stream is not None:
            return self._stream
        return sys.stderr

    def configure(
        self,
        *,
        output_format: OutputFormat | None = None,
        color_mode: ColorMode | None = None,
        progress_mode: ProgressMode | None = None,
        quiet: bool | None = None,
    ) -> None:
        """Apply invocation-level rendering policy."""
        if output_format is not None:
            self.output_format = output_format
        if color_mode is not None:
            self.color_mode = color_mode
        if progress_mode is not None:
            self.progress_mode = progress_mode
        if quiet is not None:
            self.quiet = quiet
        # Color and terminal policy are baked into a Console at construction.
        self._consoles.clear()
        self.capabilities = TerminalCapabilities.detect(
            stream=self.stream,
            output_format=self.output_format,
            color_mode=self.color_mode,
            progress_mode=self.progress_mode,
        )

    def _console(self, *, error: bool = False) -> Console:
        """Return the one console bound to this stream.

        Consoles are cached rather than rebuilt per call because a Rich live
        display only knows to render ordinary prints *above* itself when those
        prints go through the same console instance.
        """
        if self._session_console is not None:
            return self._session_console
        cached = self._consoles.get(error)
        if cached is None:
            cached = Console(
                file=self.error_stream if error else self.stream,
                theme=AGENTFLOW_THEME,
                no_color=not self.capabilities.color,
                force_terminal=self.capabilities.color,
                highlight=False,
                soft_wrap=False,
            )
            self._consoles[error] = cached
        return cached

    @property
    def glyphs(self) -> Glyphs:
        """Symbol set matching this terminal's encoding support."""
        return glyphs_for(self.capabilities.unicode)

    @property
    def fullscreen_active(self) -> bool:
        """Whether this invocation currently owns the alternate screen."""
        return self._screen_active

    def start_fullscreen_session(self) -> bool:
        """Run the whole command on a painted alternate screen.

        This switches the terminal buffer directly instead of wrapping the
        session in a live display: a live display re-homes the cursor before
        every write, which would overwrite each line the command prints.
        """
        if self.fullscreen_active or self.quiet or not self.capabilities.animation:
            return False
        console = self._console()
        if not console.is_terminal:
            return False

        console.set_alt_screen(True)
        if self.capabilities.color:
            console.file.write(_FULLSCREEN_PAINT)
            console.file.flush()
        self._session_console = console
        self._screen_active = True
        return True

    def end_fullscreen_session(self) -> None:
        """Hold the alternate screen for review, then restore the terminal.

        Releasing an alternate screen discards everything drawn on it, so the
        session pauses first — otherwise a fast command would erase its own
        result before the user could read it.
        """
        if not self._screen_active:
            return
        console = self._session_console
        self._screen_active = False
        self._session_console = None
        if console is None:
            return

        self._hold_for_review(console)
        if self.capabilities.color:
            console.file.write(_FULLSCREEN_RESET)
            console.file.flush()
        console.set_alt_screen(False)
        console.show_cursor(True)

    def _hold_for_review(self, console: Console) -> None:
        glyphs = self.glyphs
        console.print()
        console.print(
            gradient_rule(max(min(console.width, 100) - 1, 20), glyphs=glyphs, thin=True)
        )
        console.print(
            Text(
                f" {glyphs.caret} Press Enter to return to your terminal",
                style="agentflow.muted",
            )
        )
        if not sys.stdin.isatty():
            return
        with contextlib.suppress(Exception):
            sys.stdin.readline()

    @property
    def _structured(self) -> bool:
        return self.capabilities.output_format in {OutputFormat.JSON, OutputFormat.JSONL}

    def _emit_event(self, event: str, message: str, **data: Any) -> None:
        payload = {
            "schema": "agentflow.cli/v1",
            "type": event,
            "message": message,
            **data,
        }
        print(json.dumps(payload, ensure_ascii=False, default=str), file=self.stream, flush=True)

    def print_banner(
        self,
        title: str,
        subtitle: str | None = None,
        color: str = "cyan",
        width: int = 50,
    ) -> None:
        """Render a compact section heading or a panel on an interactive terminal."""
        if self.quiet:
            return
        if self._structured:
            self._emit_event("section", title, subtitle=subtitle)
            return
        if self.capabilities.output_format == OutputFormat.PLAIN:
            print(f"\n== {title} ==", file=self.stream)
            if subtitle:
                print(subtitle, file=self.stream)
            print("", file=self.stream)
            return

        body = f"[agentflow.title]{title}[/agentflow.title]"
        if subtitle:
            body += f"\n[agentflow.muted]{subtitle}[/agentflow.muted]"
        self._console().print(Panel.fit(body, border_style=color, padding=(0, 1), width=width))

    def command_header(
        self,
        command: str,
        subtitle: str | None = None,
        *,
        color: str = "cyan",
    ) -> None:
        """Render an animated command identity when the terminal supports it."""
        if self.quiet:
            return
        if self._structured:
            self._emit_event("section", command, subtitle=subtitle)
            return
        if self.capabilities.output_format == OutputFormat.PLAIN:
            self.print_banner(command.title(), subtitle, color=color)
            return
        if not self.capabilities.animation:
            # Still branded, just motionless — reduced motion should not mean
            # a downgrade in the information the header carries.
            render_session_header(
                self._console(),
                command=command,
                subtitle=subtitle,
                glyphs=self.glyphs,
                version=CLI_VERSION,
            )
            return
        render_command_intro(
            self._console(),
            command=command,
            subtitle=subtitle,
            unicode=self.capabilities.unicode,
            persistent_screen=self.fullscreen_active,
        )

    def timeline(
        self,
        title: str | None = None,
        *,
        steps: Sequence[tuple[str, str]] = (),
    ) -> Timeline:
        """Create a multi-stage progress timeline for the current output mode.

        Declaring ``steps`` up front lets the user see the whole plan the moment
        work begins, with pending stages dimmed and the running one animated.
        """
        if self.quiet:
            return QuietTimeline(steps)
        if self._structured:
            return StructuredTimeline(emit=self._emit_event_data, title=title, steps=steps)
        if not self.capabilities.animation:
            return StaticTimeline(
                glyphs=self.glyphs,
                emit=self._write_line,
                title=title,
                steps=steps,
            )
        return LiveTimeline(self._console(), glyphs=self.glyphs, title=title, steps=steps)

    def progress_run(self, title: str, *, total: int) -> ProgressRun:
        """Create a determinate progress display with a running pass/fail tally."""
        if self.quiet:
            return QuietProgressRun(total=total, title=title)
        if self._structured:
            return StructuredProgressRun(total=total, title=title, emit=self._emit_event_data)
        if not self.capabilities.animation:
            return StaticProgressRun(
                total=total,
                title=title,
                glyphs=self.glyphs,
                emit=self._write_line,
            )
        return LiveProgressRun(self._console(), total=total, title=title, glyphs=self.glyphs)

    def _emit_event_data(self, event: str, message: str, data: dict[str, Any]) -> None:
        self._emit_event(event, message, **data)

    def _write_line(self, message: str) -> None:
        """Write one pre-formatted line without interpreting console markup."""
        if self.capabilities.output_format == OutputFormat.PLAIN:
            print(message, file=self.stream)
            return
        self._console().print(Text(message))

    def success(self, message: str, emoji: bool = True) -> None:
        if self.quiet:
            return
        symbol = "✓" if self.capabilities.unicode else "OK"
        self._message("success", message, symbol if emoji else "", error=False)

    def error(self, message: str, emoji: bool = True) -> None:
        symbol = "✗" if self.capabilities.unicode else "X"
        self._message("error", message, symbol if emoji else "", error=True)

    def info(self, message: str, emoji: bool = True) -> None:
        if self.quiet:
            return
        self._message("info", message, "i" if emoji else "", error=False)

    def warning(self, message: str, emoji: bool = True) -> None:
        if self.quiet:
            return
        self._message("warning", message, "!" if emoji else "", error=False)

    def _message(
        self,
        level: str,
        message: str,
        symbol: str,
        *,
        error: bool,
    ) -> None:
        if self._structured:
            self._emit_event(level, message)
            return
        prefix = f"{symbol} " if symbol else ""
        if self.capabilities.output_format == OutputFormat.PLAIN:
            print(f"{prefix}{message}", file=self.error_stream if error else self.stream)
            return
        self._console(error=error).print(f"[agentflow.{level}]{prefix}{message}[/agentflow.{level}]")

    def emphasize(self, message: str) -> None:
        if self.quiet:
            return
        self._message(
            "info",
            message,
            "•" if self.capabilities.unicode else "*",
            error=False,
        )

    def print_list(
        self,
        items: list[str],
        title: str | None = None,
        bullet: str = "•",
    ) -> None:
        if self.quiet:
            return
        if self._structured:
            self._emit_event("list", title or "", items=items)
            return
        console = self._console()
        if title:
            console.print(f"\n[bold]{title}[/bold]")
        for item in items:
            console.print(f"  {bullet} {item}")

    def print_key_value_pairs(
        self,
        pairs: dict[str, Any],
        title: str | None = None,
        indent: int = 2,
    ) -> None:
        if self.quiet:
            return
        if self._structured:
            self._emit_event("data", title or "", data=pairs)
            return
        console = self._console()
        if title:
            console.print(f"\n[bold]{title}[/bold]")
        pad = " " * indent
        for key, value in pairs.items():
            console.print(f"{pad}[agentflow.muted]{key}[/agentflow.muted]  {value}")

    def print_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str | None = None,
    ) -> None:
        if self.quiet:
            return
        if self._structured:
            records = [
                {
                    header: row[index] if index < len(row) else ""
                    for index, header in enumerate(headers)
                }
                for row in rows
            ]
            self._emit_event("table", title or "", columns=headers, rows=records)
            return

        table = Table(title=title, header_style="bold cyan", show_lines=False)
        for header in headers:
            table.add_column(str(header), overflow="fold")
        for row in rows:
            table.add_row(*(str(row[i]) if i < len(row) else "" for i in range(len(headers))))
        self._console().print(table)

    @contextmanager
    def status(self, message: str, *, spinner: str = "dots12") -> Iterator[Status | None]:
        """Show an indeterminate status when animation is safe."""
        if self._structured:
            self._emit_event("progress_start", message)
            try:
                yield None
            except Exception:
                self._emit_event("progress_end", message, status="failed")
                raise
            else:
                self._emit_event("progress_end", message, status="completed")
            return
        if self.quiet or not self.capabilities.animation:
            if not self.quiet and self.capabilities.progress_mode == ProgressMode.PLAIN:
                self.info(message, emoji=False)
            yield None
            return
        with self._console().status(
            f"[agentflow.progress]{message}[/agentflow.progress]",
            spinner=spinner,
            spinner_style="agentflow.brand",
        ) as status:
            yield status

    @contextmanager
    def activity(
        self,
        message: str,
        *,
        done: str | None = None,
        spinner: str = "dots12",
    ) -> Iterator[Status | None]:
        """Animate a bounded task and persist a timed completion state."""
        started = time.monotonic()
        try:
            with self.status(message, spinner=spinner) as status:
                yield status
        except Exception:
            elapsed = time.monotonic() - started
            self.error(f"{message} failed after {elapsed:.1f}s")
            raise
        else:
            elapsed = time.monotonic() - started
            self.success(f"{done or message} ({elapsed:.1f}s)")

    def completion_screen(
        self,
        title: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        next_steps: list[str] | None = None,
    ) -> None:
        """Render a polished final state for a completed workflow."""
        if self.quiet:
            return
        if self._structured:
            self._emit_event(
                "completion",
                message,
                title=title,
                details=details or {},
                next_steps=next_steps or [],
            )
            return
        if self.capabilities.output_format == OutputFormat.PLAIN:
            self.success(f"{title}: {message}")
            if details:
                self.print_key_value_pairs(details)
            if next_steps:
                self.print_list(next_steps, title="Next steps", bullet="->")
            return

        console = self._console()
        rows = list((details or {}).items())
        steps = list(next_steps or [])
        total = len(rows) + len(steps)

        if not self.capabilities.animation or not total:
            console.print(self._completion_panel(title, message, rows, steps, total))
            return

        # Reveal one row at a time so the result reads as an outcome landing
        # rather than a wall of text appearing at once.
        with Live(
            console=console,
            auto_refresh=False,
            transient=False,
            redirect_stdout=False,
            redirect_stderr=False,
        ) as live:
            for visible in range(total + 1):
                live.update(
                    self._completion_panel(title, message, rows, steps, visible),
                    refresh=True,
                )
                time.sleep(0.05)

    def _completion_panel(
        self,
        title: str,
        message: str,
        rows: list[tuple[str, Any]],
        steps: list[str],
        visible: int,
    ) -> Panel:
        """Build the completion panel with only its first ``visible`` rows shown."""
        glyphs = self.glyphs
        body = Text()
        body.append(f"{glyphs.check} ", style="agentflow.success")
        body.append(message, style="agentflow.command")

        shown = 0
        if rows:
            label_width = max(len(str(key)) for key, _ in rows) + 2
            body.append("\n")
            for key, value in rows:
                if shown >= visible:
                    break
                body.append(f"\n  {key!s:<{label_width}}", style="agentflow.muted")
                body.append(str(value), style="agentflow.command")
                shown += 1

        if steps and visible > len(rows):
            body.append("\n\n")
            body.append("Next", style="bold #a78bfa")
            for step in steps:
                if shown >= visible:
                    break
                body.append(f"\n  {glyphs.arrow} ", style="agentflow.accent")
                body.append(step, style="agentflow.command")
                shown += 1

        return Panel(
            body,
            title=gradient_text(f" {title} ", bold=True),
            title_align="left",
            box=box.ROUNDED,
            border_style="#7c3aed",
            padding=(1, 2),
        )


output = OutputFormatter()


def print_banner(title: str, subtitle: str | None = None, color: str = "cyan") -> None:
    output.print_banner(title, subtitle, color)


def success(message: str, emoji: bool = True) -> None:
    output.success(message, emoji)


def error(message: str, emoji: bool = True) -> None:
    output.error(message, emoji)


def info(message: str, emoji: bool = True) -> None:
    output.info(message, emoji)


def warning(message: str, emoji: bool = True) -> None:
    output.warning(message, emoji)


def emphasize(message: str) -> None:
    output.emphasize(message)
