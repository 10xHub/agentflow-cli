"""Output formatting utilities for the CLI - ANIMATION STYLE C: RAIN DROP CASCADE + LOCK."""

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
        """Rain Drop Cascade: characters fall from above and lock into position with flash."""
        import os
        import sys
        import time
        import random
        from rich.live import Live
        from rich.text import Text

        if (
            self._logo_animated
            or "pytest" in sys.modules
            or os.environ.get("ENVIRONMENT") == "pytest"
            or self.stream != sys.stdout
        ):
            return

        self._logo_animated = True

        ascii_logo_lines = [
            r"    ___   ______ ______ _   __ ______   ______ __     ____  _      __",
            r"   /   | / ____// ____// | / //_  __/  / ____// /    / __ \| | /| / /",
            r"  / /| |/ / __ / __/  /  |/ /  / /    / __/  / /    / / / /| |/ |/ / ",
            r" / ___ / /_/ // /___ / /|  /  / /    / /    / /___ / /_/ / |  /|  /  ",
            r"/_/  |_\____//_____//_/ |_/  /_/    /_/    /_____/ \____/  |__/|_/  ",
        ]

        NUM_ROWS = len(ascii_logo_lines)
        MAX_LEN = max(len(l) for l in ascii_logo_lines)

        class FallingChar:
            def __init__(self, char, target_row, target_col, delay):
                self.char = char
                self.target_row = target_row
                self.target_col = target_col
                self.current_row = -random.randint(1, 8)
                self.delay = delay
                self.landed = False
                self.flash_frames = 0
                self.speed = random.uniform(0.4, 1.2)

        def build_rain_frame(chars, frame):
            grid = [[" " for _ in range(MAX_LEN)] for _ in range(NUM_ROWS)]
            color_grid = [["" for _ in range(MAX_LEN)] for _ in range(NUM_ROWS)]

            for fc in chars:
                if frame < fc.delay:
                    continue
                if fc.landed:
                    grid[fc.target_row][fc.target_col] = fc.char
                    if fc.flash_frames > 0:
                        color_grid[fc.target_row][fc.target_col] = "bold #ffffff"
                        fc.flash_frames -= 1
                    else:
                        color_grid[fc.target_row][fc.target_col] = "#00ffff"
                else:
                    display_row = int(fc.current_row)
                    if 0 <= display_row < NUM_ROWS:
                        grid[display_row][fc.target_col] = fc.char
                        color_grid[display_row][fc.target_col] = "#005f5f"
                    trail_row = display_row - 1
                    if 0 <= trail_row < NUM_ROWS:
                        if grid[trail_row][fc.target_col] == " ":
                            grid[trail_row][fc.target_col] = "|"
                            color_grid[trail_row][fc.target_col] = "#003333"

            t = Text()
            for r in range(NUM_ROWS):
                for c in range(MAX_LEN):
                    ch = grid[r][c]
                    color = color_grid[r][c]
                    if color and ch != " ":
                        t.append(ch, style=color)
                    else:
                        t.append(ch)
                t.append("\n")
            return t

        random.seed(42)
        chars = []
        for row_idx, line in enumerate(ascii_logo_lines):
            for col_idx, ch in enumerate(line):
                if ch != " ":
                    delay = int(col_idx * 0.3) + random.randint(0, 5)
                    chars.append(FallingChar(ch, row_idx, col_idx, delay))

        total_frames = 55

        self.console.print("\n")
        with Live(build_rain_frame(chars, 0), console=self.console, auto_refresh=False, transient=False) as live:
            for frame in range(total_frames):
                for fc in chars:
                    if frame < fc.delay or fc.landed:
                        continue
                    fc.current_row += fc.speed
                    if fc.current_row >= fc.target_row:
                        fc.current_row = fc.target_row
                        fc.landed = True
                        fc.flash_frames = 3

                live.update(build_rain_frame(chars, frame))
                live.refresh()
                time.sleep(0.04)

            # Force land everything
            for fc in chars:
                fc.landed = True
                fc.flash_frames = 0

            # Final color sweep
            for sc in ["#ff00ff", "#d700ff", "#af00ff", "#0087ff", "#00ffff"]:
                st = Text()
                for line in ascii_logo_lines:
                    st.append(line + "\n", style=f"bold {sc}")
                live.update(st)
                live.refresh()
                time.sleep(0.08)

            # Settle
            ft = Text()
            for line in ascii_logo_lines:
                ft.append(line + "\n", style="bold #00ffff")
            live.update(ft)
            live.refresh()
            time.sleep(0.3)
        self.console.print("\n")

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
