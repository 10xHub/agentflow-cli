"""CLI command modules."""

from abc import ABC, abstractmethod
from typing import Any

from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.logger import CLILoggerMixin


class BaseCommand(ABC, CLILoggerMixin):
    """Base class for all CLI commands."""

    def __init__(self, output: OutputFormatter | None = None) -> None:
        """Initialize the base command.

        Args:
            output: Output formatter instance
        """
        super().__init__()
        self.output = output or OutputFormatter()

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Safely print to console if output has console print support."""
        if hasattr(self.output, "console"):
            self.output.console.print(*args, **kwargs)

    import contextlib
    @contextlib.contextmanager
    def spinner(self, message: str):
        """Safely show a spinner if output has spinner method support."""
        if hasattr(self.output, "spinner"):
            with self.output.spinner(message):
                yield
        else:
            yield

    def animate_text(self, text: str, delay: float = 0.015) -> None:
        """Safely print animated text if output has animate_text support."""
        if hasattr(self.output, "animate_text"):
            self.output.animate_text(text, delay)
        elif hasattr(self.output, "info"):
            self.output.info(text)

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> int:
        """Execute the command.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """

    def handle_error(self, error: Exception) -> int:
        """Handle command errors consistently.

        Args:
            error: Exception that occurred

        Returns:
            Appropriate exit code
        """
        self.logger.error("Command failed: %s", error)

        # Import here to avoid circular imports
        from agentflow_cli.cli.exceptions import PyagenityCLIError

        if isinstance(error, PyagenityCLIError):
            self.output.error(error.message)
            return error.exit_code

        self.output.error(f"Unexpected error: {error}")
        return 1
