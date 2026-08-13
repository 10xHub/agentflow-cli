"""Tests for centralized CLI logging."""

from __future__ import annotations

import logging
from io import StringIO

from agentflow_cli.cli.logger import (
    CLILoggerMixin,
    create_debug_logger,
    get_logger,
    setup_cli_logging,
)


def teardown_function() -> None:
    root = logging.getLogger("agentflowcli")
    root.handlers.clear()


def test_mixin_uses_named_child_logger() -> None:
    class ExampleCommand(CLILoggerMixin):
        pass

    command = ExampleCommand()
    assert command.logger.name == "agentflowcli.ExampleCommand"
    assert command.logger.propagate is True
    assert command.logger.handlers == []


def test_children_share_single_root_handler() -> None:
    setup_cli_logging(verbose=True)
    first = get_logger("first")
    second = get_logger("second")
    root = logging.getLogger("agentflowcli")
    assert len(root.handlers) == 1
    assert first.handlers == []
    assert second.handlers == []
    assert first.getEffectiveLevel() == logging.DEBUG
    assert second.getEffectiveLevel() == logging.DEBUG


def test_quiet_and_verbose_levels() -> None:
    setup_cli_logging(verbose=True)
    assert logging.getLogger("agentflowcli").level == logging.DEBUG
    setup_cli_logging(quiet=True, verbose=True)
    assert logging.getLogger("agentflowcli").level == logging.ERROR


def test_reconfiguration_replaces_handler() -> None:
    setup_cli_logging()
    original = logging.getLogger("agentflowcli").handlers[0]
    setup_cli_logging(level=logging.WARNING)
    root = logging.getLogger("agentflowcli")
    assert len(root.handlers) == 1
    assert root.handlers[0] is not original
    assert root.handlers[0].level == logging.WARNING


def test_custom_stream_is_isolated() -> None:
    stream = StringIO()
    logger = get_logger("captured", level=logging.WARNING, stream=stream)
    logger.warning("visible")
    assert "visible" in stream.getvalue()
    assert logger.propagate is False
    assert len(logger.handlers) == 1


def test_debug_logger_enables_debug_globally() -> None:
    logger = create_debug_logger("debug")
    assert logger.getEffectiveLevel() == logging.DEBUG
    assert logging.getLogger("agentflowcli").handlers[0].level == logging.DEBUG
