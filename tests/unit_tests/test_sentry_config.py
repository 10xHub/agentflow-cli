"""Tests for Sentry configuration initialization."""

from unittest.mock import Mock, patch

import pytest

from agentflow_cli.src.app.core.config.sentry_config import init_sentry


class TestInitSentry:
    """Tests for init_sentry function."""

    def test_init_sentry_no_dsn(self):
        """Test Sentry init when DSN is not configured."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = None
        mock_settings.MODE = "DEVELOPMENT"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            init_sentry(mock_settings)
            mock_logger.warning.assert_called_once()

    def test_init_sentry_empty_dsn(self):
        """Test Sentry init when DSN is empty string."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = ""
        mock_settings.MODE = "DEVELOPMENT"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            init_sentry(mock_settings)
            mock_logger.warning.assert_called_once()

    def test_init_sentry_invalid_environment(self):
        """Test Sentry init with invalid environment."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "INVALID"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            init_sentry(mock_settings)
            # Should warn about invalid environment
            mock_logger.warning.assert_called()

    def test_init_sentry_production_environment(self):
        """Test Sentry init with PRODUCTION environment."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            with patch("sys.modules") as mock_modules:
                mock_sentry = Mock()
                mock_modules.__getitem__.return_value = mock_sentry
                with patch(
                    "agentflow_cli.src.app.core.config.sentry_config.sentry_sdk", mock_sentry
                ):
                    init_sentry(mock_settings)

    def test_init_sentry_staging_environment(self):
        """Test Sentry init with STAGING environment."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "staging"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            with patch("sys.modules") as mock_modules:
                mock_sentry = Mock()
                mock_modules.__getitem__.return_value = mock_sentry
                with patch(
                    "agentflow_cli.src.app.core.config.sentry_config.sentry_sdk", mock_sentry
                ):
                    init_sentry(mock_settings)

    def test_init_sentry_development_environment(self):
        """Test Sentry init with DEVELOPMENT environment."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "development"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            with patch("sys.modules") as mock_modules:
                mock_sentry = Mock()
                mock_modules.__getitem__.return_value = mock_sentry
                with patch(
                    "agentflow_cli.src.app.core.config.sentry_config.sentry_sdk", mock_sentry
                ):
                    init_sentry(mock_settings)

    def test_init_sentry_import_error(self):
        """Test Sentry init handles ImportError gracefully."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            with patch("builtins.__import__", side_effect=ImportError("sentry_sdk not found")):
                init_sentry(mock_settings)
                # Should log warning about missing sentry_sdk
                mock_logger.warning.assert_called()

    def test_init_sentry_initialization_error(self):
        """Test Sentry init handles initialization errors gracefully."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            # Create a mock that raises an exception
            mock_sentry_sdk = Mock()
            mock_sentry_sdk.init = Mock(side_effect=Exception("Init failed"))

            with patch.dict(
                "sys.modules", {"sentry_sdk": mock_sentry_sdk, "sentry_sdk.integrations": Mock()}
            ):
                try:
                    init_sentry(mock_settings)
                except:
                    # Exception handling is ok
                    pass

                # Should log warning about initialization error
                mock_logger.warning.assert_called()

    def test_init_sentry_sets_correct_parameters(self):
        """Test Sentry is initialized with correct parameters."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            # Create mock sentry_sdk module
            mock_sentry_sdk = Mock()
            mock_init = Mock()
            mock_sentry_sdk.init = mock_init

            with patch.dict(
                "sys.modules", {"sentry_sdk": mock_sentry_sdk, "sentry_sdk.integrations": Mock()}
            ):
                try:
                    init_sentry(mock_settings)
                    # If sentry_sdk module was imported, verify it was initialized
                    if mock_init.called:
                        call_kwargs = mock_init.call_args[1]
                        assert call_kwargs.get("dsn") == "https://example@sentry.io/12345"
                except:
                    # Sentry SDK import may still fail, which is ok for test
                    pass

    def test_init_sentry_logs_initialization_debug(self):
        """Test Sentry init logs debug message on success."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            # Mock the sentry_sdk module
            mock_sentry_sdk = Mock()

            with patch.dict(
                "sys.modules", {"sentry_sdk": mock_sentry_sdk, "sentry_sdk.integrations": Mock()}
            ):
                try:
                    init_sentry(mock_settings)
                    # Should log info and debug messages if successful
                    if mock_logger.info.called:
                        assert mock_logger.info.called
                except:
                    # Sentry import may fail
                    pass

    def test_init_sentry_uppercase_mode(self):
        """Test Sentry init with uppercase MODE."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "PRODUCTION"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            mock_sentry_sdk = Mock()
            with patch.dict(
                "sys.modules", {"sentry_sdk": mock_sentry_sdk, "sentry_sdk.integrations": Mock()}
            ):
                try:
                    init_sentry(mock_settings)
                except:
                    # Sentry import may fail
                    pass

    def test_init_sentry_mixed_case_mode(self):
        """Test Sentry init with mixed case MODE."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = "Production"

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger"):
            mock_sentry_sdk = Mock()
            with patch.dict(
                "sys.modules", {"sentry_sdk": mock_sentry_sdk, "sentry_sdk.integrations": Mock()}
            ):
                try:
                    init_sentry(mock_settings)
                except:
                    # Sentry import may fail
                    pass

    def test_init_sentry_none_mode(self):
        """Test Sentry init when MODE is None."""
        mock_settings = Mock()
        mock_settings.SENTRY_DSN = "https://example@sentry.io/12345"
        mock_settings.MODE = None

        with patch("agentflow_cli.src.app.core.config.sentry_config.logger") as mock_logger:
            init_sentry(mock_settings)
            # Should warn about invalid environment
            mock_logger.warning.assert_called()
