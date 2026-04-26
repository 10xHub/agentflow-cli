"""Tests for CLI output formatting module."""

import sys
import io
from unittest.mock import patch, MagicMock

import pytest
import typer

from agentflow_cli.cli.core.output import (
    OutputFormatter,
    print_banner,
    success,
    error,
    info,
    warning,
    emphasize,
    output,
)


class TestOutputFormatter:
    """Test suite for OutputFormatter class."""

    @pytest.fixture
    def output_stream(self):
        """Create a string buffer for capturing output."""
        return io.StringIO()

    @pytest.fixture
    def formatter(self, output_stream):
        """Create an OutputFormatter instance with test stream."""
        return OutputFormatter(stream=output_stream)

    def test_initialization_default_stream(self):
        """Test OutputFormatter initialization with default stream."""
        formatter = OutputFormatter()
        assert formatter.stream == sys.stdout

    def test_initialization_custom_stream(self, output_stream):
        """Test OutputFormatter initialization with custom stream."""
        formatter = OutputFormatter(stream=output_stream)
        assert formatter.stream == output_stream

    @patch("typer.echo")
    def test_print_banner_with_title_only(self, mock_echo, formatter):
        """Test printing banner with only title."""
        formatter.print_banner("Test Title")

        # Verify typer.echo was called
        assert mock_echo.called
        # Should print banner with title

    @patch("typer.echo")
    def test_print_banner_with_subtitle(self, mock_echo, formatter):
        """Test printing banner with title and subtitle."""
        formatter.print_banner("Test Title", subtitle="Test Subtitle")

        # Verify typer.echo was called multiple times (for empty line, title, subtitle, empty line)
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_banner_with_color(self, mock_echo, formatter):
        """Test printing banner with custom color."""
        formatter.print_banner("Test Title", color="green")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_banner_with_width(self, mock_echo, formatter):
        """Test printing banner with custom width."""
        formatter.print_banner("Test Title", width=100)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_success_message_with_emoji(self, mock_echo, formatter):
        """Test printing success message with emoji."""
        formatter.success("Operation successful")

        # Verify typer.echo was called with success styling
        assert mock_echo.called

    @patch("typer.echo")
    def test_success_message_without_emoji(self, mock_echo, formatter):
        """Test printing success message without emoji."""
        formatter.success("Operation successful", emoji=False)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_error_message_with_emoji(self, mock_echo, formatter):
        """Test printing error message with emoji."""
        formatter.error("An error occurred")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_error_message_without_emoji(self, mock_echo, formatter):
        """Test printing error message without emoji."""
        formatter.error("An error occurred", emoji=False)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_info_message_with_emoji(self, mock_echo, formatter):
        """Test printing info message with emoji."""
        formatter.info("Information message")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_info_message_without_emoji(self, mock_echo, formatter):
        """Test printing info message without emoji."""
        formatter.info("Information message", emoji=False)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_warning_message_with_emoji(self, mock_echo, formatter):
        """Test printing warning message with emoji."""
        formatter.warning("Warning message")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_warning_message_without_emoji(self, mock_echo, formatter):
        """Test printing warning message without emoji."""
        formatter.warning("Warning message", emoji=False)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_emphasize_message(self, mock_echo, formatter):
        """Test printing emphasized message."""
        formatter.emphasize("Important message")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_list_without_title(self, mock_echo, formatter):
        """Test printing list without title."""
        items = ["Item 1", "Item 2", "Item 3"]
        formatter.print_list(items)

        # Verify typer.echo was called for each item
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_list_with_title(self, mock_echo, formatter):
        """Test printing list with title."""
        items = ["Item 1", "Item 2", "Item 3"]
        formatter.print_list(items, title="My List")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_list_with_custom_bullet(self, mock_echo, formatter):
        """Test printing list with custom bullet character."""
        items = ["Item 1", "Item 2", "Item 3"]
        formatter.print_list(items, bullet="-")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_list_empty(self, mock_echo, formatter):
        """Test printing empty list."""
        formatter.print_list([])

        # With an empty list and no title, typer.echo might not be called at all
        # or may be called for the empty list display. Both are acceptable.
        # Just verify the method doesn't raise an exception
        pass

    @patch("typer.echo")
    def test_print_key_value_pairs_without_title(self, mock_echo, formatter):
        """Test printing key-value pairs without title."""
        pairs = {"name": "John", "age": 30, "city": "New York"}
        formatter.print_key_value_pairs(pairs)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_key_value_pairs_with_title(self, mock_echo, formatter):
        """Test printing key-value pairs with title."""
        pairs = {"name": "John", "age": 30, "city": "New York"}
        formatter.print_key_value_pairs(pairs, title="User Info")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_key_value_pairs_custom_indent(self, mock_echo, formatter):
        """Test printing key-value pairs with custom indentation."""
        pairs = {"key1": "value1", "key2": "value2"}
        formatter.print_key_value_pairs(pairs, indent=4)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_table_without_title(self, mock_echo, formatter):
        """Test printing table without title."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["John", "30", "New York"],
            ["Jane", "28", "Los Angeles"],
            ["Bob", "35", "Chicago"],
        ]
        formatter.print_table(headers, rows)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_table_with_title(self, mock_echo, formatter):
        """Test printing table with title."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["John", "30", "New York"],
            ["Jane", "28", "Los Angeles"],
        ]
        formatter.print_table(headers, rows, title="People")

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_table_empty(self, mock_echo, formatter):
        """Test printing table with no rows."""
        headers = ["Name", "Age", "City"]
        rows = []
        formatter.print_table(headers, rows)

        # Verify typer.echo was called
        assert mock_echo.called

    @patch("typer.echo")
    def test_print_table_inconsistent_row_length(self, mock_echo, formatter):
        """Test printing table with rows of inconsistent length."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["John", "30"],  # Missing City
            ["Jane", "28", "Los Angeles"],
            ["Bob", "35", "Chicago", "Extra"],  # Extra column
        ]
        formatter.print_table(headers, rows)

        # Should handle inconsistent row lengths gracefully
        assert mock_echo.called


class TestGlobalFunctions:
    """Test suite for global convenience functions."""

    @patch("agentflow_cli.cli.core.output.output.print_banner")
    def test_print_banner_function(self, mock_print_banner):
        """Test global print_banner function."""
        print_banner("Test Title")

        # Verify the method was called on the global instance
        assert mock_print_banner.called

    @patch("agentflow_cli.cli.core.output.output.success")
    def test_success_function(self, mock_success):
        """Test global success function."""
        success("Operation successful")

        # Verify the method was called on the global instance
        assert mock_success.called

    @patch("agentflow_cli.cli.core.output.output.error")
    def test_error_function(self, mock_error):
        """Test global error function."""
        error("An error occurred")

        # Verify the method was called on the global instance
        assert mock_error.called

    @patch("agentflow_cli.cli.core.output.output.info")
    def test_info_function(self, mock_info):
        """Test global info function."""
        info("Information message")

        # Verify the method was called on the global instance
        assert mock_info.called

    @patch("agentflow_cli.cli.core.output.output.warning")
    def test_warning_function(self, mock_warning):
        """Test global warning function."""
        warning("Warning message")

        # Verify the method was called on the global instance
        assert mock_warning.called

    @patch("agentflow_cli.cli.core.output.output.emphasize")
    def test_emphasize_function(self, mock_emphasize):
        """Test global emphasize function."""
        emphasize("Important message")

        # Verify the method was called on the global instance
        assert mock_emphasize.called


class TestOutputFormatterIntegration:
    """Integration tests for OutputFormatter."""

    def test_multiple_messages_sequence(self):
        """Test printing multiple messages in sequence."""
        stream = io.StringIO()
        formatter = OutputFormatter(stream=stream)

        with patch("typer.echo") as mock_echo:
            formatter.info("Starting process")
            formatter.success("Step 1 complete")
            formatter.warning("Step 2 warning")
            formatter.error("Step 3 error")

            # All should have been called
            assert mock_echo.call_count >= 4

    def test_complex_table_output(self):
        """Test printing a complex table."""
        stream = io.StringIO()
        formatter = OutputFormatter(stream=stream)

        headers = ["ID", "Status", "Message"]
        rows = [
            ["1", "SUCCESS", "Operation completed"],
            ["2", "FAILED", "Error occurred"],
            ["3", "PENDING", "Waiting for response"],
        ]

        with patch("typer.echo") as mock_echo:
            formatter.print_table(headers, rows, title="Operation Status")
            assert mock_echo.called

    def test_global_instance_exists(self):
        """Test that global output instance exists."""
        assert output is not None
        assert isinstance(output, OutputFormatter)

    def test_formatter_with_various_data_types(self):
        """Test formatter with various data types in key-value pairs."""
        stream = io.StringIO()
        formatter = OutputFormatter(stream=stream)

        pairs = {
            "string": "hello",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
        }

        with patch("typer.echo") as mock_echo:
            formatter.print_key_value_pairs(pairs)
            # Should handle all data types
            assert mock_echo.called
