"""Unit tests for security configuration warnings."""

import os
from unittest.mock import patch

import pytest

from agentflow_cli.src.app.core.config.settings import Settings, get_settings


def test_mode_normalization():
    """Test that MODE is normalized to lowercase."""
    with patch.dict(os.environ, {"MODE": "PRODUCTION"}):
        settings = Settings()
        assert settings.MODE == "production"

    with patch.dict(os.environ, {"MODE": "Development"}):
        settings = Settings()
        assert settings.MODE == "development"


def test_cors_wildcard_warning_in_production(caplog):
    """Test warning for CORS wildcard in production."""
    with patch.dict(os.environ, {"MODE": "production", "ORIGINS": "*"}):
        settings = Settings()
        assert "CORS ORIGINS='*' in production" in caplog.text


def test_cors_wildcard_no_warning_in_development(caplog):
    """Test no warning for CORS wildcard in development."""
    with patch.dict(os.environ, {"MODE": "development", "ORIGINS": "*"}):
        settings = Settings()
        assert "CORS ORIGINS" not in caplog.text or "production" not in caplog.text


def test_debug_mode_warning_in_production(caplog):
    """Test warning for DEBUG mode enabled in production."""
    with patch.dict(os.environ, {"MODE": "production", "IS_DEBUG": "true"}):
        settings = Settings()
        assert "DEBUG mode is enabled in production" in caplog.text


def test_docs_enabled_warning_in_production(caplog):
    """Test warning for API docs enabled in production."""
    with patch.dict(os.environ, {"MODE": "production"}):
        settings = Settings()
        # Default has DOCS_PATH="/docs"
        assert "API documentation endpoints are enabled" in caplog.text


def test_allowed_host_wildcard_warning_in_production(caplog):
    """Test warning for ALLOWED_HOST wildcard in production."""
    with patch.dict(os.environ, {"MODE": "production", "ALLOWED_HOST": "*"}):
        settings = Settings()
        assert "ALLOWED_HOST='*' in production" in caplog.text


def test_no_warnings_in_development(caplog):
    """Test that no security warnings appear in development mode."""
    with patch.dict(os.environ, {"MODE": "development"}):
        settings = Settings()
        assert "SECURITY WARNING" not in caplog.text


def test_multiple_warnings_in_production(caplog):
    """Test that multiple warnings can appear together."""
    with patch.dict(
        os.environ,
        {
            "MODE": "production",
            "ORIGINS": "*",
            "IS_DEBUG": "true",
            "ALLOWED_HOST": "*",
        },
    ):
        settings = Settings()

        log_text = caplog.text
        assert "CORS ORIGINS='*'" in log_text
        assert "DEBUG mode is enabled" in log_text
        assert "ALLOWED_HOST='*'" in log_text


def test_max_request_size_default():
    """Test that MAX_REQUEST_SIZE has correct default."""
    settings = Settings()
    assert settings.MAX_REQUEST_SIZE == 10 * 1024 * 1024  # 10MB


def test_max_request_size_configurable():
    """Test that MAX_REQUEST_SIZE is configurable via env var."""
    with patch.dict(os.environ, {"MAX_REQUEST_SIZE": "5242880"}):  # 5MB
        settings = Settings()
        assert settings.MAX_REQUEST_SIZE == 5242880


def test_settings_caching():
    """Test that get_settings returns cached instance."""
    # Clear cache first
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
