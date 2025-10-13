"""Logging configuration for the Pyagenity CLI."""

import logging
import sys
from typing import TextIO

from .constants import LOG_DATE_FORMAT, LOG_FORMAT


class CLILoggerMixin:
    """Mixin to add logging capabilities to CLI commands."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the logger mixin."""
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)


def get_logger(
    name: str,
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Get a configured logger for the CLI.

    Args:
        name: Logger name
        level: Logging level
        stream: Output stream (defaults to stderr)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"agentflowcli.{name}")

    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def setup_cli_logging(
    level: int = logging.INFO,
    quiet: bool = False,
    verbose: bool = False,
) -> None:
    """Setup logging for the entire CLI application.

    Args:
        level: Base logging level
        quiet: Suppress all output except errors
        verbose: Enable verbose output
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG

    # Configure root logger for the CLI
    root_logger = logging.getLogger("agentflowcli")
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.propagate = False


def create_debug_logger(name: str) -> logging.Logger:
    """Create a debug-level logger for development.

    Args:
        name: Logger name

    Returns:
        Debug logger instance
    """
    return get_logger(name, level=logging.DEBUG)
