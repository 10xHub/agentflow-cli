"""
Unit tests for auth_backend module.

Tests cover the verify_current_user function which is the integration point
for JWT authentication in the application.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from agentflow_cli.src.app.core.auth.auth_backend import verify_current_user
from agentflow_cli.src.app.core.auth.base_auth import BaseAuth
from agentflow_cli.src.app.core.config.graph_config import GraphConfig


class MockBaseAuth(BaseAuth):
    """Mock implementation of BaseAuth for testing."""

    def __init__(self, return_value: dict[str, Any] | None = None, raise_exception: bool = False):
        self._return_value = return_value
        self._raise_exception = raise_exception

    def authenticate(
        self, request: Request | None, res: Response, credential: HTTPAuthorizationCredentials
    ) -> dict[str, Any] | None:
        if self._raise_exception:
            raise ValueError("Authentication failed")
        return self._return_value


class TestVerifyCurrentUser:
    """Test suite for verify_current_user function."""

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock FastAPI Response object."""
        return Response()

    @pytest.fixture
    def mock_credentials(self) -> HTTPAuthorizationCredentials:
        """Create mock HTTP Authorization credentials."""
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    @pytest.fixture
    def mock_graph_config_no_auth(self) -> MagicMock:
        """Create a mock GraphConfig that returns None for auth_config."""
        config = MagicMock(spec=GraphConfig)
        config.auth_config.return_value = None
        return config

    @pytest.fixture
    def mock_graph_config_jwt_auth(self) -> MagicMock:
        """Create a mock GraphConfig that returns JWT auth config."""
        config = MagicMock(spec=GraphConfig)
        config.auth_config.return_value = {"method": "jwt"}
        return config

    def test_returns_empty_dict_when_no_auth_backend_configured(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_no_auth: MagicMock,
    ):
        """Test that empty dict is returned when auth is not configured."""
        mock_auth_backend = MockBaseAuth(return_value={"user_id": "123"})

        result = verify_current_user(
            request=None,
            response=mock_response,
            credential=mock_credentials,
            config=mock_graph_config_no_auth,
            auth_backend=mock_auth_backend,
        )

        assert result == {}

    def test_returns_empty_dict_when_auth_backend_is_none(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that empty dict is returned when auth_backend is None."""
        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=None,
            )

            assert result == {}
            mock_logger.error.assert_called_once_with("Auth backend is not configured")

    def test_returns_user_dict_on_successful_authentication(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that user dict is returned when authentication succeeds."""
        expected_user = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "admin",
        }
        mock_auth_backend = MockBaseAuth(return_value=expected_user)

        result = verify_current_user(
            request=None,
            response=mock_response,
            credential=mock_credentials,
            config=mock_graph_config_jwt_auth,
            auth_backend=mock_auth_backend,
        )

        assert result == expected_user
        assert result["user_id"] == "user-123"

    def test_returns_empty_dict_when_authenticate_returns_none(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that empty dict is returned when authenticate returns None."""
        mock_auth_backend = MockBaseAuth(return_value=None)

        result = verify_current_user(
            request=None,
            response=mock_response,
            credential=mock_credentials,
            config=mock_graph_config_jwt_auth,
            auth_backend=mock_auth_backend,
        )

        assert result == {}

    def test_logs_error_when_user_dict_missing_user_id(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that error is logged when authenticated user dict has no user_id."""
        user_without_id = {"email": "test@example.com", "role": "admin"}
        mock_auth_backend = MockBaseAuth(return_value=user_without_id)

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            # Should still return the user dict even without user_id
            assert result == user_without_id
            mock_logger.error.assert_called_once_with(
                "Authentication failed: 'user_id' not found in user info"
            )

    def test_does_not_log_error_when_user_dict_has_user_id(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that no error is logged when authenticated user dict has user_id."""
        user_with_id = {"user_id": "123", "email": "test@example.com"}
        mock_auth_backend = MockBaseAuth(return_value=user_with_id)

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            assert result == user_with_id
            mock_logger.error.assert_not_called()

    def test_does_not_log_error_when_authenticate_returns_empty_dict(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that no error is logged when authenticate returns empty dict."""
        mock_auth_backend = MockBaseAuth(return_value={})

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            # Empty dict is falsy, so the 'if user' condition fails
            # and we return {} without logging
            assert result == {}
            mock_logger.error.assert_not_called()

    def test_returns_user_with_numeric_user_id(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that numeric user_id works correctly."""
        user_with_numeric_id = {"user_id": 12345, "email": "test@example.com"}
        mock_auth_backend = MockBaseAuth(return_value=user_with_numeric_id)

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            assert result == user_with_numeric_id
            # numeric user_id still passes the 'in' check
            mock_logger.error.assert_not_called()

    def test_returns_user_with_empty_string_user_id(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that empty string user_id is accepted (key exists)."""
        user_with_empty_id = {"user_id": "", "email": "test@example.com"}
        mock_auth_backend = MockBaseAuth(return_value=user_with_empty_id)

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            assert result == user_with_empty_id
            # Empty string user_id still passes 'in' check (key exists)
            mock_logger.error.assert_not_called()

    def test_returns_user_with_none_user_id(
        self,
        mock_response: Response,
        mock_credentials: HTTPAuthorizationCredentials,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that None user_id is accepted (key exists)."""
        user_with_none_id = {"user_id": None, "email": "test@example.com"}
        mock_auth_backend = MockBaseAuth(return_value=user_with_none_id)

        with patch("agentflow_cli.src.app.core.auth.auth_backend.logger") as mock_logger:
            result = verify_current_user(
                request=None,
                response=mock_response,
                credential=mock_credentials,
                config=mock_graph_config_jwt_auth,
                auth_backend=mock_auth_backend,
            )

            assert result == user_with_none_id
            # None user_id still passes 'in' check (key exists)
            mock_logger.error.assert_not_called()


class TestVerifyCurrentUserWithNullCredentials:
    """Test verify_current_user with null credentials scenarios."""

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock FastAPI Response object."""
        return Response()

    @pytest.fixture
    def mock_graph_config_jwt_auth(self) -> MagicMock:
        """Create a mock GraphConfig that returns JWT auth config."""
        config = MagicMock(spec=GraphConfig)
        config.auth_config.return_value = {"method": "jwt"}
        return config

    def test_passes_null_credentials_to_auth_backend(
        self,
        mock_response: Response,
        mock_graph_config_jwt_auth: MagicMock,
    ):
        """Test that null credentials are passed to auth backend."""
        # Create a mock that tracks calls
        mock_auth = MagicMock(spec=BaseAuth)
        mock_auth.authenticate.return_value = {"user_id": "123"}

        verify_current_user(
            request=None,
            response=mock_response,
            credential=None,  # Null credentials
            config=mock_graph_config_jwt_auth,
            auth_backend=mock_auth,
        )

        # Verify authenticate was called with None credentials
        mock_auth.authenticate.assert_called_once_with(None, mock_response, None)
