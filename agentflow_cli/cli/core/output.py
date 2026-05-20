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
        import threading
        import atexit

        self.stream = stream or sys.stdout
        self.console = Console(file=self.stream)
        self.err_console = Console(file=sys.stderr)
        self._logo_animated = False

        # Continuous background animation support
        self._animating_active = False
        self._animating_thread = None
        self._live_logo = None
        self._logo_lock = threading.Lock()

        # Register cleanup on exit to ensure clean terminal state
        atexit.register(self.stop_logo_animation)

    def _animate_logo(self) -> None:
        """Start a gorgeous, color-cycling ASCII logo animation in the background (skipped in tests)."""
        import os
        import sys
        import time
        import threading
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
        self._animating_active = True

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

        # Initial spacing
        self.console.print("\n")

        # Start Live rendering
        self._live_logo = Live(get_frame(0), console=self.console, auto_refresh=False, transient=False)
        self._live_logo.start()

        def run_animation():
            shift = 0
            while True:
                with self._logo_lock:
                    if not self._animating_active:
                        break
                    shift += 1
                try:
                    self._live_logo.update(get_frame(shift))
                    self._live_logo.refresh()
                except Exception:
                    break
                time.sleep(0.05)

        # Launch the background animation thread
        self._animating_thread = threading.Thread(target=run_animation, daemon=True)
        self._animating_thread.start()

        # Let the animation run continuously for at least 1.2 seconds on startup
        # to guarantee a gorgeous, fluid color sweep intro sequence
        time.sleep(1.2)

    def stop_logo_animation(self) -> None:
        """Stop the background logo animation if it is running."""
        with self._logo_lock:
            if not self._animating_active:
                return
            self._animating_active = False

        if self._animating_thread:
            self._animating_thread.join(timeout=0.5)
            self._animating_thread = None

        if self._live_logo:
            try:
                self._live_logo.stop()
            except Exception:
                pass
            self._live_logo = None

        # Space out the content cleanly
        self.console.print("\n")

    def _print(self, *args, err: bool = False, **kwargs) -> None:
        """Helper to print using capture and typer.echo to satisfy unit test mocks."""
        import typer

        # Automatically stop the logo animation before printing any new content
        if self._animating_active:
            self.stop_logo_animation()

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
        text.append(">> ", style="bold yellow")
        text.append(title.upper(), style=f"bold {color}")
        text.append(" <<\n", style="bold yellow")
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
        text = Text.from_markup(f">> [bold magenta]{message}[/bold magenta] <<")
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