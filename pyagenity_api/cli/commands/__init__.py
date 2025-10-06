"""CLI command modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pyagenity_api.cli.core.output import OutputFormatter
from pyagenity_api.cli.logger import CLILoggerMixin


if TYPE_CHECKING:
    from pyagenity_api.cli.exceptions import PyagenityCLIError


class BaseCommand(ABC, CLILoggerMixin):
    """Base class for all CLI commands."""

    def __init__(self, output: OutputFormatter | None = None) -> None:
        """Initialize the base command.

        Args:
            output: Output formatter instance
        """
        super().__init__()
        self.output = output or OutputFormatter()

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
        from pyagenity_api.cli.exceptions import PyagenityCLIError

        if isinstance(error, PyagenityCLIError):
            self.output.error(error.message)
            return error.exit_code
        else:
            self.output.error(f"Unexpected error: {error}")
            return 1
