"""
Comprehensive unit tests for JwtAuth class.

These tests cover all edge cases and scenarios for JWT authentication:
- Null credentials
- Missing JWT configuration (secret key, algorithm)
- Expired tokens
- Invalid/malformed tokens
- Valid tokens without user_id
- Valid tokens with user_id (successful auth)
- Bearer prefix handling
- WWW-Authenticate header setting
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials

from agentflow_cli.src.app.core.auth.jwt_auth import JwtAuth
from agentflow_cli.src.app.core.exceptions.user_exception import UserAccountError


# Test constants
TEST_SECRET_KEY = "test-super-secret-key-for-testing-purposes"
TEST_ALGORITHM = "HS256"


class TestJwtAuth:
    """Test suite for JwtAuth.authenticate method."""

    @pytest.fixture
    def jwt_auth(self) -> JwtAuth:
        """Create a JwtAuth instance for testing."""
        return JwtAuth()

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock FastAPI Response object."""
        return Response()

    @pytest.fixture
    def valid_token_payload(self) -> dict:
        """Create a valid JWT payload with user_id."""
        return {
            "user_id": "user-123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def jwt_env_vars(self):
        """Set up JWT environment variables for tests."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET_KEY,
                "JWT_ALGORITHM": TEST_ALGORITHM,
            },
        ):
            yield

    def create_token(
        self,
        payload: dict,
        secret: str = TEST_SECRET_KEY,
        algorithm: str = TEST_ALGORITHM,
    ) -> str:
        """Helper method to create a JWT token."""
        return jwt.encode(payload, secret, algorithm=algorithm)

    def create_credentials(self, token: str) -> HTTPAuthorizationCredentials:
        """Helper method to create HTTPAuthorizationCredentials."""
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # =========================================================================
    # Test: Null credentials
    # =========================================================================
    def test_authenticate_with_null_credentials_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that null credentials raise UserAccountError with REVOKED_TOKEN."""
        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, None)

        assert exc_info.value.error_code == "REVOKED_TOKEN"
        assert "Invalid token" in exc_info.value.message
        assert exc_info.value.status_code == 403

    # =========================================================================
    # Test: Missing JWT settings
    # =========================================================================
    def test_authenticate_missing_jwt_secret_key_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that missing JWT_SECRET_KEY raises UserAccountError."""
        with patch.dict(
            os.environ,
            {"JWT_ALGORITHM": TEST_ALGORITHM},
            clear=True,
        ):
            credentials = self.create_credentials("some-token")

            with pytest.raises(UserAccountError) as exc_info:
                jwt_auth.authenticate(mock_response, credentials)

            assert exc_info.value.error_code == "JWT_SETTINGS_NOT_CONFIGURED"
            assert "JWT settings are not configured" in exc_info.value.message

    def test_authenticate_missing_jwt_algorithm_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that missing JWT_ALGORITHM raises UserAccountError."""
        with patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": TEST_SECRET_KEY},
            clear=True,
        ):
            credentials = self.create_credentials("some-token")

            with pytest.raises(UserAccountError) as exc_info:
                jwt_auth.authenticate(mock_response, credentials)

            assert exc_info.value.error_code == "JWT_SETTINGS_NOT_CONFIGURED"
            assert "JWT settings are not configured" in exc_info.value.message

    def test_authenticate_missing_both_jwt_settings_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that missing both JWT settings raises UserAccountError."""
        with patch.dict(os.environ, {}, clear=True):
            credentials = self.create_credentials("some-token")

            with pytest.raises(UserAccountError) as exc_info:
                jwt_auth.authenticate(mock_response, credentials)

            assert exc_info.value.error_code == "JWT_SETTINGS_NOT_CONFIGURED"

    # =========================================================================
    # Test: Expired token
    # =========================================================================
    def test_authenticate_expired_token_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that expired token raises UserAccountError with EXPIRED_TOKEN."""
        expired_payload = {
            "user_id": "user-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = self.create_token(expired_payload)
        credentials = self.create_credentials(token)

        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, credentials)

        assert exc_info.value.error_code == "EXPIRED_TOKEN"
        assert "Token has expired" in exc_info.value.message

    # =========================================================================
    # Test: Invalid token
    # =========================================================================
    def test_authenticate_malformed_token_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that malformed token raises UserAccountError with INVALID_TOKEN."""
        credentials = self.create_credentials("not-a-valid-jwt-token")

        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, credentials)

        assert exc_info.value.error_code == "INVALID_TOKEN"
        assert "Invalid token" in exc_info.value.message

    def test_authenticate_token_with_wrong_secret_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that token signed with wrong secret raises UserAccountError."""
        payload = {
            "user_id": "user-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # Sign with a different secret
        token = self.create_token(payload, secret="wrong-secret-key")
        credentials = self.create_credentials(token)

        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, credentials)

        assert exc_info.value.error_code == "INVALID_TOKEN"

    def test_authenticate_token_with_wrong_algorithm_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that token signed with wrong algorithm raises UserAccountError."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET_KEY,
                "JWT_ALGORITHM": "HS384",  # Different from token's HS256
            },
        ):
            payload = {
                "user_id": "user-123",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            }
            # Token signed with HS256 but server expects HS384
            token = self.create_token(payload, algorithm="HS256")
            credentials = self.create_credentials(token)

            with pytest.raises(UserAccountError) as exc_info:
                jwt_auth.authenticate(mock_response, credentials)

            assert exc_info.value.error_code == "INVALID_TOKEN"

    def test_authenticate_empty_token_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that empty token raises UserAccountError."""
        credentials = self.create_credentials("")

        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, credentials)

        assert exc_info.value.error_code == "INVALID_TOKEN"

    # =========================================================================
    # Test: Token without user_id
    # =========================================================================
    def test_authenticate_token_without_user_id_raises_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that valid token without user_id raises UserAccountError."""
        payload_without_user_id = {
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = self.create_token(payload_without_user_id)
        credentials = self.create_credentials(token)

        with pytest.raises(UserAccountError) as exc_info:
            jwt_auth.authenticate(mock_response, credentials)

        assert exc_info.value.error_code == "INVALID_TOKEN"
        assert "user_id missing" in exc_info.value.message

    # =========================================================================
    # Test: Successful authentication
    # =========================================================================
    def test_authenticate_valid_token_returns_decoded_payload(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that valid token with user_id returns decoded payload."""
        token = self.create_token(valid_token_payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"

    def test_authenticate_returns_all_custom_claims(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that all custom claims in token are returned."""
        payload = {
            "user_id": "user-456",
            "email": "custom@example.com",
            "role": "admin",
            "permissions": ["read", "write", "delete"],
            "organization_id": "org-789",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = self.create_token(payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result["user_id"] == "user-456"
        assert result["email"] == "custom@example.com"
        assert result["role"] == "admin"
        assert result["permissions"] == ["read", "write", "delete"]
        assert result["organization_id"] == "org-789"

    # =========================================================================
    # Test: Bearer prefix handling
    # =========================================================================
    def test_authenticate_strips_bearer_prefix_lowercase(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that 'bearer ' prefix (lowercase) is stripped from token."""
        actual_token = self.create_token(valid_token_payload)
        token_with_prefix = f"bearer {actual_token}"
        credentials = self.create_credentials(token_with_prefix)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"

    def test_authenticate_strips_bearer_prefix_uppercase(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that 'Bearer ' prefix (capitalized) is stripped from token."""
        actual_token = self.create_token(valid_token_payload)
        token_with_prefix = f"Bearer {actual_token}"
        credentials = self.create_credentials(token_with_prefix)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"

    def test_authenticate_strips_bearer_prefix_mixed_case(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that 'BEARER ' prefix (mixed case) is stripped from token."""
        actual_token = self.create_token(valid_token_payload)
        token_with_prefix = f"BEARER {actual_token}"
        credentials = self.create_credentials(token_with_prefix)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"

    def test_authenticate_works_without_bearer_prefix(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that token without bearer prefix still works."""
        token = self.create_token(valid_token_payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"

    # =========================================================================
    # Test: WWW-Authenticate header
    # =========================================================================
    def test_authenticate_sets_www_authenticate_header(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
        valid_token_payload: dict,
    ):
        """Test that WWW-Authenticate header is set on successful auth."""
        token = self.create_token(valid_token_payload)
        credentials = self.create_credentials(token)

        jwt_auth.authenticate(mock_response, credentials)

        assert "WWW-Authenticate" in mock_response.headers
        assert mock_response.headers["WWW-Authenticate"] == 'Bearer realm="auth_required"'

    # =========================================================================
    # Test: Edge cases
    # =========================================================================
    def test_authenticate_with_minimal_valid_token(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test authentication with minimal valid token (just user_id)."""
        minimal_payload = {"user_id": "minimal-user"}
        token = self.create_token(minimal_payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "minimal-user"

    def test_authenticate_with_numeric_user_id(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that numeric user_id in token works correctly."""
        payload = {
            "user_id": 12345,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = self.create_token(payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == 12345

    def test_authenticate_with_uuid_user_id(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that UUID user_id in token works correctly."""
        uuid_user_id = "550e8400-e29b-41d4-a716-446655440000"
        payload = {
            "user_id": uuid_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = self.create_token(payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == uuid_user_id

    def test_authenticate_token_about_to_expire_still_valid(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that token about to expire (in 1 second) is still valid."""
        payload = {
            "user_id": "user-123",
            "exp": datetime.now(timezone.utc) + timedelta(seconds=30),
        }
        token = self.create_token(payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == "user-123"

    def test_authenticate_with_special_characters_in_user_id(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that special characters in user_id work correctly."""
        special_user_id = "user+test@example.com"
        payload = {
            "user_id": special_user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = self.create_token(payload)
        credentials = self.create_credentials(token)

        result = jwt_auth.authenticate(mock_response, credentials)

        assert result is not None
        assert result["user_id"] == special_user_id

    # =========================================================================
    # Test: Different algorithms
    # =========================================================================
    def test_authenticate_with_hs384_algorithm(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test authentication with HS384 algorithm."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET_KEY,
                "JWT_ALGORITHM": "HS384",
            },
        ):
            payload = {
                "user_id": "user-hs384",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            }
            token = self.create_token(payload, algorithm="HS384")
            credentials = self.create_credentials(token)

            result = jwt_auth.authenticate(mock_response, credentials)

            assert result is not None
            assert result["user_id"] == "user-hs384"

    def test_authenticate_with_hs512_algorithm(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test authentication with HS512 algorithm."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": TEST_SECRET_KEY,
                "JWT_ALGORITHM": "HS512",
            },
        ):
            payload = {
                "user_id": "user-hs512",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            }
            token = self.create_token(payload, algorithm="HS512")
            credentials = self.create_credentials(token)

            result = jwt_auth.authenticate(mock_response, credentials)

            assert result is not None
            assert result["user_id"] == "user-hs512"

    # =========================================================================
    # Test: Logger is called on InvalidTokenError
    # =========================================================================
    def test_authenticate_logs_invalid_token_error(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
        jwt_env_vars,
    ):
        """Test that logger.exception is called when InvalidTokenError occurs."""
        with patch("agentflow_cli.src.app.core.auth.jwt_auth.logger") as mock_logger:
            credentials = self.create_credentials("invalid-token")

            with pytest.raises(UserAccountError):
                jwt_auth.authenticate(mock_response, credentials)

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert "JWT AUTH ERROR" in call_args[0][0]


class TestJwtAuthIntegration:
    """Integration tests for JwtAuth with real JWT encoding/decoding."""

    @pytest.fixture
    def jwt_auth(self) -> JwtAuth:
        """Create a JwtAuth instance for testing."""
        return JwtAuth()

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock FastAPI Response object."""
        return Response()

    def test_full_authentication_flow(self, jwt_auth: JwtAuth, mock_response: Response):
        """Test complete authentication flow from token creation to validation."""
        secret = "integration-test-secret-key"
        algorithm = "HS256"

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": secret,
                "JWT_ALGORITHM": algorithm,
            },
        ):
            # Create a realistic token payload
            # Note: We skip 'aud' claim because PyJWT validates it by default
            # and the current JwtAuth implementation doesn't configure audience
            payload = {
                "user_id": "user-integration-test",
                "email": "integration@test.com",
                "name": "Integration Test User",
                "role": "developer",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=24),
                "iss": "test-issuer",
            }

            # Encode token
            token = jwt.encode(payload, secret, algorithm=algorithm)
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Authenticate
            result = jwt_auth.authenticate(mock_response, credentials)

            # Verify all claims are returned
            assert result["user_id"] == "user-integration-test"
            assert result["email"] == "integration@test.com"
            assert result["name"] == "Integration Test User"
            assert result["role"] == "developer"
            assert result["iss"] == "test-issuer"

            # Verify header is set
            assert mock_response.headers["WWW-Authenticate"] == 'Bearer realm="auth_required"'

    def test_token_roundtrip_with_complex_payload(
        self,
        jwt_auth: JwtAuth,
        mock_response: Response,
    ):
        """Test that complex payloads survive the encode/decode roundtrip."""
        secret = "complex-payload-test-secret"
        algorithm = "HS256"

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": secret,
                "JWT_ALGORITHM": algorithm,
            },
        ):
            complex_payload = {
                "user_id": "complex-user",
                "metadata": {
                    "nested": {
                        "deeply": "nested value",
                    },
                },
                "tags": ["tag1", "tag2", "tag3"],
                "count": 42,
                "active": True,
                "nullable": None,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            }

            token = jwt.encode(complex_payload, secret, algorithm=algorithm)
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            result = jwt_auth.authenticate(mock_response, credentials)

            assert result["user_id"] == "complex-user"
            assert result["metadata"]["nested"]["deeply"] == "nested value"
            assert result["tags"] == ["tag1", "tag2", "tag3"]
            assert result["count"] == 42
            assert result["active"] is True
            assert result["nullable"] is None
