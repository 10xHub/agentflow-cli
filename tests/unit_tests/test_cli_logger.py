"""Unit tests for CLI logger configuration."""

import logging
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from agentflow_cli.cli.logger import (
    CLILoggerMixin,
    create_debug_logger,
    get_logger,
    setup_cli_logging,
)


class TestCLILoggerMixin:
    """Test CLILoggerMixin."""

    def test_mixin_init_creates_logger(self):
        """Test that mixin initialization creates a logger."""

        class TestCommand(CLILoggerMixin):
            pass

        command = TestCommand()

        assert hasattr(command, "logger")
        assert isinstance(command.logger, logging.Logger)
        assert "TestCommand" in command.logger.name

    def test_mixin_logger_name(self):
        """Test that mixin logger has correct name format."""

        class MyCommand(CLILoggerMixin):
            pass

        command = MyCommand()

        assert command.logger.name == "agentflowcli.MyCommand"


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert "test_logger" in logger.name

    def test_get_logger_with_custom_level(self):
        """Test get_logger with custom logging level."""
        logger = get_logger("debug_logger", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_get_logger_with_custom_stream(self):
        """Test get_logger with custom stream."""
        custom_stream = StringIO()
        logger = get_logger("stream_logger", stream=custom_stream)

        assert isinstance(logger, logging.Logger)
        # Logger should have a handler
        assert len(logger.handlers) > 0

    def test_get_logger_returns_same_logger_on_multiple_calls(self):
        """Test that multiple calls return the same logger instance."""
        logger1 = get_logger("same_logger")
        logger2 = get_logger("same_logger")

        assert logger1 is logger2

    def test_get_logger_handler_configured(self):
        """Test that logger has properly configured handler."""
        logger = get_logger("handler_test")

        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.INFO

    def test_get_logger_formatter_configured(self):
        """Test that logger handler has formatter."""
        logger = get_logger("formatter_test")

        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter is not None

    def test_get_logger_prevents_propagation(self):
        """Test that logger doesn't propagate to root logger."""
        logger = get_logger("no_propagation_test")

        assert logger.propagate is False

    def test_get_logger_with_info_level(self):
        """Test get_logger with INFO level."""
        logger = get_logger("info_logger", level=logging.INFO)

        assert logger.level == logging.INFO

    def test_get_logger_with_error_level(self):
        """Test get_logger with ERROR level."""
        logger = get_logger("error_logger", level=logging.ERROR)

        assert logger.level == logging.ERROR

    def test_get_logger_with_warning_level(self):
        """Test get_logger with WARNING level."""
        logger = get_logger("warning_logger", level=logging.WARNING)

        assert logger.level == logging.WARNING


class TestSetupCLILogging:
    """Test setup_cli_logging function."""

    def teardown_method(self):
        """Clean up loggers after each test."""
        root_logger = logging.getLogger("agentflowcli")
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_cli_logging_default(self):
        """Test setup_cli_logging with default parameters."""
        setup_cli_logging()

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0

    def test_setup_cli_logging_with_quiet(self):
        """Test setup_cli_logging with quiet mode."""
        setup_cli_logging(quiet=True)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.ERROR

    def test_setup_cli_logging_with_verbose(self):
        """Test setup_cli_logging with verbose mode."""
        setup_cli_logging(verbose=True)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.DEBUG

    def test_setup_cli_logging_quiet_overrides_verbose(self):
        """Test that quiet mode takes precedence over verbose."""
        setup_cli_logging(quiet=True, verbose=True)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.ERROR

    def test_setup_cli_logging_with_custom_level(self):
        """Test setup_cli_logging with custom level."""
        setup_cli_logging(level=logging.WARNING)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.WARNING

    def test_setup_cli_logging_removes_existing_handlers(self):
        """Test that setup_cli_logging removes existing handlers."""
        root_logger = logging.getLogger("agentflowcli")

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)

        initial_count = len(root_logger.handlers)

        # Setup logging - should remove old handler
        setup_cli_logging()

        # Should have exactly one handler after setup
        assert len(root_logger.handlers) == 1
        assert dummy_handler not in root_logger.handlers

    def test_setup_cli_logging_handler_configured(self):
        """Test that handler is properly configured."""
        setup_cli_logging(level=logging.DEBUG)

        root_logger = logging.getLogger("agentflowcli")
        handler = root_logger.handlers[0]

        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.DEBUG

    def test_setup_cli_logging_prevents_propagation(self):
        """Test that root logger doesn't propagate."""
        setup_cli_logging()

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.propagate is False

    def test_setup_cli_logging_verbose_debug_level(self):
        """Test verbose mode sets DEBUG level."""
        setup_cli_logging(verbose=True)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.DEBUG

    def test_setup_cli_logging_quiet_error_level(self):
        """Test quiet mode sets ERROR level."""
        setup_cli_logging(quiet=True)

        root_logger = logging.getLogger("agentflowcli")
        assert root_logger.level == logging.ERROR


class TestCreateDebugLogger:
    """Test create_debug_logger function."""

    def test_create_debug_logger_returns_logger(self):
        """Test that create_debug_logger returns a Logger instance."""
        logger = create_debug_logger("debug_test")

        assert isinstance(logger, logging.Logger)

    def test_create_debug_logger_sets_debug_level(self):
        """Test that debug logger has DEBUG level."""
        logger = create_debug_logger("debug_level_test")

        assert logger.level == logging.DEBUG

    def test_create_debug_logger_name_format(self):
        """Test that debug logger has correct name format."""
        logger = create_debug_logger("my_debug")

        assert "my_debug" in logger.name
        assert "agentflowcli" in logger.name

    def test_create_debug_logger_has_handler(self):
        """Test that debug logger has a handler."""
        logger = create_debug_logger("debug_handler_test")

        assert len(logger.handlers) > 0

    def test_create_debug_logger_handler_is_stream_handler(self):
        """Test that debug logger uses StreamHandler."""
        logger = create_debug_logger("stream_handler_test")

        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

    def test_create_debug_logger_stderr_by_default(self):
        """Test that debug logger uses stderr by default."""
        logger = create_debug_logger("stderr_test")

        handler = logger.handlers[0]
        assert handler.stream == sys.stderr or handler.stream is None

    def test_create_debug_logger_formatter_configured(self):
        """Test that debug logger has formatter."""
        logger = create_debug_logger("formatter_debug_test")

        handler = logger.handlers[0]
        assert handler.formatter is not None

    def test_create_debug_logger_prevents_propagation(self):
        """Test that debug logger doesn't propagate."""
        logger = create_debug_logger("no_prop_debug_test")

        assert logger.propagate is False


class TestLoggerIntegration:
    """Integration tests for logger functionality."""

    def test_get_logger_and_setup_cli_logging_work_together(self):
        """Test that get_logger works with setup_cli_logging."""
        setup_cli_logging(verbose=True)

        logger = get_logger("integration_test")

        assert logger.level == logging.DEBUG or logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_multiple_loggers_independent(self):
        """Test that multiple loggers can coexist."""
        logger1 = get_logger("logger1", level=logging.INFO)
        logger2 = get_logger("logger2", level=logging.DEBUG)

        assert logger1.name != logger2.name
        assert logger1.level == logging.INFO
        assert logger2.level == logging.DEBUG

    def test_cli_logger_mixin_with_setup(self):
        """Test CLILoggerMixin with setup_cli_logging."""
        setup_cli_logging(verbose=True)

        class TestCmd(CLILoggerMixin):
            pass

        cmd = TestCmd()
        assert isinstance(cmd.logger, logging.Logger)
        assert len(cmd.logger.handlers) > 0
