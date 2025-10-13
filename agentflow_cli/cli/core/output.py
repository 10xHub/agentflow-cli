"""Output formatting utilities for the CLI."""

from __future__ import annotations

import sys
from typing import Any, TextIO

import typer

from agentflow_cli.cli.constants import (
    EMOJI_ERROR,
    EMOJI_INFO,
    EMOJI_SPARKLE,
    EMOJI_SUCCESS,
    Colors,
)


class OutputFormatter:
    """Handles formatted output for the CLI."""

    def __init__(self, stream: TextIO | None = None) -> None:
        """Initialize the output formatter.

        Args:
            stream: Output stream (defaults to stdout)
        """
        self.stream = stream or sys.stdout

    def print_banner(
        self,
        title: str,
        subtitle: str | None = None,
        color: str = "cyan",
        width: int = 50,
    ) -> None:
        """Print a formatted banner.

        Args:
            title: Banner title
            subtitle: Optional subtitle
            color: Color name for the banner
            width: Banner width
        """
        colored_title = Colors.colorize(f"== {title} ==", color)

        typer.echo("")
        typer.echo(colored_title, file=self.stream)
        if subtitle:
            typer.echo(subtitle, file=self.stream)
        typer.echo("", file=self.stream)

    def success(self, message: str, emoji: bool = True) -> None:
        """Print a success message.

        Args:
            message: Success message
            emoji: Whether to include emoji
        """
        prefix = f"{EMOJI_SUCCESS}  " if emoji else ""
        formatted = Colors.colorize(f"{prefix}{message}", "green")
        typer.echo(f"\n{formatted}", file=self.stream)

    def error(self, message: str, emoji: bool = True) -> None:
        """Print an error message.

        Args:
            message: Error message
            emoji: Whether to include emoji
        """
        prefix = f"{EMOJI_ERROR}  " if emoji else ""
        formatted = Colors.colorize(f"{prefix}{message}", "red")
        typer.echo(f"\n{formatted}", err=True)

    def info(self, message: str, emoji: bool = True) -> None:
        """Print an info message.

        Args:
            message: Info message
            emoji: Whether to include emoji
        """
        prefix = f"{EMOJI_INFO}  " if emoji else ""
        formatted = Colors.colorize(f"{prefix}{message}", "blue")
        typer.echo(f"\n{formatted}", file=self.stream)

    def warning(self, message: str, emoji: bool = True) -> None:
        """Print a warning message.

        Args:
            message: Warning message
            emoji: Whether to include emoji
        """
        prefix = f"{EMOJI_ERROR}  " if emoji else ""
        formatted = Colors.colorize(f"{prefix}{message}", "yellow")
        typer.echo(f"\n{formatted}", file=self.stream)

    def emphasize(self, message: str) -> None:
        """Print an emphasized message with sparkle emoji.

        Args:
            message: Message to emphasize
        """
        formatted = f"{EMOJI_SPARKLE}  {message}"
        typer.echo(f"\n{formatted}", file=self.stream)

    def print_list(
        self,
        items: list[str],
        title: str | None = None,
        bullet: str = "•",
    ) -> None:
        """Print a formatted list.

        Args:
            items: List items to print
            title: Optional list title
            bullet: Bullet character
        """
        if title:
            typer.echo(f"\n{title}:", file=self.stream)

        for item in items:
            typer.echo(f"  {bullet} {item}", file=self.stream)

    def print_key_value_pairs(
        self,
        pairs: dict[str, Any],
        title: str | None = None,
        indent: int = 2,
    ) -> None:
        """Print key-value pairs in a formatted way.

        Args:
            pairs: Dictionary of key-value pairs
            title: Optional title for the section
            indent: Indentation level
        """
        if title:
            typer.echo(f"\n{title}:", file=self.stream)

        indent_str = " " * indent
        for key, value in pairs.items():
            typer.echo(f"{indent_str}{key}: {value}", file=self.stream)

    def print_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str | None = None,
    ) -> None:
        """Print a simple table.

        Args:
            headers: Table headers
            rows: Table rows
            title: Optional table title
        """
        if title:
            typer.echo(f"\n{title}:", file=self.stream)

        # Calculate column widths
        all_rows = [headers, *rows]
        col_widths = [
            max(len(str(row[i])) for row in all_rows if i < len(row)) for i in range(len(headers))
        ]

        # Print headers
        header_row = " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(len(headers)))
        typer.echo(f"\n{header_row}", file=self.stream)
        typer.echo("-" * len(header_row), file=self.stream)

        # Print rows
        for row in rows:
            row_str = " | ".join(
                str(row[i] if i < len(row) else "").ljust(col_widths[i])
                for i in range(len(headers))
            )
            typer.echo(row_str, file=self.stream)


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
