"""Adaptive terminal output utilities for the CLI."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TextIO

from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from agentflow_cli.cli.capabilities import (
    ColorMode,
    OutputFormat,
    ProgressMode,
    TerminalCapabilities,
)
from agentflow_cli.cli.core.animations import render_command_intro


_THEME = Theme(
    {
        "agentflow.success": "bold green",
        "agentflow.error": "bold red",
        "agentflow.warning": "bold yellow",
        "agentflow.info": "cyan",
        "agentflow.muted": "dim",
        "agentflow.title": "bold magenta",
        "agentflow.brand": "bold cyan",
        "agentflow.command": "bold white",
        "agentflow.progress": "cyan",
    }
)


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
        self.capabilities = TerminalCapabilities.detect(
            stream=self.stream,
            output_format=self.output_format,
            color_mode=self.color_mode,
            progress_mode=self.progress_mode,
        )

    def _console(self, *, error: bool = False) -> Console:
        return Console(
            file=self.error_stream if error else self.stream,
            theme=_THEME,
            no_color=not self.capabilities.color,
            force_terminal=self.capabilities.color,
            highlight=False,
            soft_wrap=False,
        )

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
        if not self.capabilities.animation:
            self.print_banner(command.title(), subtitle, color=color)
            return
        render_command_intro(
            self._console(),
            command=command,
            subtitle=subtitle,
            unicode=self.capabilities.unicode,
        )

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

        body = Text()
        symbol = "✓" if self.capabilities.unicode else "OK"
        body.append(f"{symbol} {message}", style="agentflow.success")
        if details:
            for key, value in details.items():
                body.append(f"\n{key:<12}", style="agentflow.muted")
                body.append(str(value), style="agentflow.command")
        if next_steps:
            body.append("\n\nNext steps", style="bold")
            arrow = "→" if self.capabilities.unicode else "->"
            for step in next_steps:
                body.append(f"\n  {arrow} {step}")
        self._console().print(
            Panel(
                body,
                title=f"[agentflow.title]{title}[/agentflow.title]",
                border_style="green",
                padding=(1, 2),
            )
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
