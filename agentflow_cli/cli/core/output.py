"""Output formatting utilities for the CLI."""

from __future__ import annotations

import sys
import time
from typing import Any, TextIO

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box

from agentflow_cli.cli.constants import (
    EMOJI_ERROR,
    EMOJI_INFO,
    EMOJI_SPARKLE,
    EMOJI_SUCCESS,
)


class OutputFormatter:
    """Handles formatted output for the CLI using rich aesthetics."""

    def __init__(self, stream: TextIO | None = None) -> None:
        """Initialize the output formatter with Rich Console."""
        self.stream = stream or sys.stdout
        self.console = Console(file=self.stream)
        self.err_console = Console(file=sys.stderr)
        self._logo_animated = False

    def _animate_logo(self) -> None:
        """Draw a gorgeous, color-cycling ASCII logo animation on startup (skipped in tests)."""
        import os
        import sys
        import time
        from rich.live import Live
        from rich.text import Text

        # Skip animation if we are running in pytest/test suites or stream is not stdout
        if (
            self._logo_animated
            or "pytest" in sys.modules
            or os.environ.get("ENVIRONMENT") == "pytest"
            or self.stream != sys.stdout
        ):
            return

        self._logo_animated = True

        ascii_logo = r"""
    ___   ______ ______ _   __ ______   ______ __     ____  _      __
   /   | / ____// ____// | / //_  __/  / ____// /    / __ \| | /| / /
  / /| |/ / __ / __/  /  |/ /  / /    / __/  / /    / / / /| |/ |/ / 
 / ___ / /_/ // /___ / /|  /  / /    / /    / /___ / /_/ / |  /|  /  
/_/  |_\____//_____//_/ |_/  /_/    /_/    /_____/ \____/  |__/|_/  
""".strip("\n")

        colors = [
            "#ff00ff", "#d700ff", "#af00ff", "#8700ff", "#5f00ff",
            "#0087ff", "#00afff", "#00d7ff", "#00ffff", "#00ffaf"
        ]

        def get_frame(shift: int) -> Text:
            logo_text = Text()
            lines = ascii_logo.split("\n")
            for i, line in enumerate(lines):
                color_idx = (shift + i) % len(colors)
                logo_text.append(line + "\n", style=colors[color_idx])
            return logo_text

        self._print("\n")
        # Run a brief 10-frame color sweep (takes ~0.4s)
        with Live(get_frame(0), refresh_per_second=25, console=self.console) as live:
            for i in range(10):
                time.sleep(0.04)
                live.update(get_frame(i))
        self._print("\n")

    def _print(self, *args, err: bool = False, **kwargs) -> None:
        """Helper to print using capture and typer.echo to satisfy unit test mocks."""
        import typer
        console = self.err_console if err else self.console
        with console.capture() as capture:
            console.print(*args, **kwargs)
        text = capture.get()
        typer.echo(text, file=sys.stderr if err else self.stream, nl=False, err=err)

    def print_banner(
        self,
        title: str,
        subtitle: str | None = None,
        color: str = "cyan",
        width: int = 50,
    ) -> None:
        """Print a visually stunning, formatted banner inside a premium Panel."""
        self._animate_logo()
        text = Text()
        text.append("✨ ", style="bold yellow")
        text.append(title.upper(), style=f"bold {color}")
        text.append(" ✨\n", style="bold yellow")
        if subtitle:
            text.append(subtitle, style="italic dim white")

        panel = Panel(
            text,
            border_style=f"bold {color}",
            box=box.ROUNDED,
            expand=False,
            padding=(1, 4),
        )
        self._print("")
        self._print(panel)
        self._print("")

    def success(self, message: str, emoji: bool = True) -> None:
        """Print a modern success message in a clean green panel."""
        prefix = f"{EMOJI_SUCCESS}  " if emoji else ""
        text = Text.from_markup(f"[bold green]{prefix}Success:[/bold green] [white]{message}[/white]")
        panel = Panel(
            text,
            border_style="green",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 2),
        )
        self._print("")
        self._print(panel)

    def error(self, message: str, emoji: bool = True) -> None:
        """Print a high-visibility error message in a bold red panel."""
        prefix = f"{EMOJI_ERROR}  " if emoji else ""
        text = Text.from_markup(f"[bold red]{prefix}Error:[/bold red] [white]{message}[/white]")
        panel = Panel(
            text,
            border_style="red",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 2),
        )
        self._print("", err=True)
        self._print(panel, err=True)

    def info(self, message: str, emoji: bool = True) -> None:
        """Print a structured info message with modern styling."""
        prefix = f"{EMOJI_INFO}  " if emoji else ""
        text = Text.from_markup(f"[bold blue]{prefix}Info:[/bold blue] [white]{message}[/white]")
        self._print(f"\n{text}")

    def warning(self, message: str, emoji: bool = True) -> None:
        """Print a yellow warning message in a sleek yellow panel."""
        prefix = f"{EMOJI_ERROR}  " if emoji else ""
        text = Text.from_markup(f"[bold yellow]{prefix}Warning:[/bold yellow] [white]{message}[/white]")
        panel = Panel(
            text,
            border_style="yellow",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 2),
        )
        self._print("")
        self._print(panel)

    def emphasize(self, message: str) -> None:
        """Print an emphasized message with sparkle styling."""
        text = Text.from_markup(f"✨ [bold magenta]{message}[/bold magenta] ✨")
        self._print(f"\n{text}")

    def print_list(
        self,
        items: list[str],
        title: str | None = None,
        bullet: str = "•",
    ) -> None:
        """Print a beautifully spaced bullet list."""
        if title:
            self._print(f"\n[bold cyan]{title}:[/bold cyan]")

        for item in items:
            self._print(f"  [bold yellow]{bullet}[/bold yellow] {item}")

    def print_key_value_pairs(
        self,
        pairs: dict[str, Any],
        title: str | None = None,
        indent: int = 2,
    ) -> None:
        """Print key-value metadata in a premium structured format."""
        if title:
            self._print(f"\n[bold cyan]{title}:[/bold cyan]")

        indent_str = " " * indent
        for key, value in pairs.items():
            self._print(f"{indent_str}[bold white]{key}:[/bold white] [dim white]{value}[/dim white]")

    def print_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str | None = None,
    ) -> None:
        """Print a highly polished table using Rich Table and rounded borders."""
        table = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
        if title:
            table.title = f"[bold magenta]{title}[/bold magenta]"

        for header in headers:
            table.add_column(header, style="bold white")

        for row in rows:
            table.add_row(*[str(cell) for cell in row])

        self._print("")
        self._print(table)

    def spinner(self, message: str):
        """Show a premium loading spinner context manager."""
        return self.console.status(f"[bold magenta]{message}[/bold magenta]", spinner="dots")

    def animate_text(self, text: str, delay: float = 0.015) -> None:
        """Prints text with a fluid typing/streaming animation effect."""
        for char in text:
            self._print(char, end="")
            time.sleep(delay)
        self._print("")


# Global instance for convenience
output = OutputFormatter()


# Convenience functions that use the global instance
def print_banner(title: str, subtitle: str | None = None, color: str = "cyan") -> None:
    """Print a formatted banner using the global formatter."""
    output.print_banner(title, subtitle, color)


def success(message: str, emoji: bool = True) -> None:
    """Print a success message using the global formatter."""
    output.success(message, emoji)


def error(message: str, emoji: bool = True) -> None:
    """Print an error message using the global formatter."""
    output.error(message, emoji)


def info(message: str, emoji: bool = True) -> None:
    """Print an info message using the global formatter."""
    output.info(message, emoji)


def warning(message: str, emoji: bool = True) -> None:
    """Print a warning message using the global formatter."""
    output.warning(message, emoji)


def emphasize(message: str) -> None:
    """Print an emphasized message using the global formatter."""
    output.emphasize(message)
