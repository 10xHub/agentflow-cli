"""Unit tests for RequirePermission authentication and authorization dependency."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.path_params = {}
    return request


@pytest.fixture
def mock_response():
    """Create a mock FastAPI response."""
    return MagicMock(spec=Response)


@pytest.fixture
def mock_credential():
    """Create a mock HTTP Bearer credential."""
    credential = MagicMock(spec=HTTPAuthorizationCredentials)
    credential.credentials = "test-token"
    return credential


@pytest.fixture
def mock_config():
    """Create a mock GraphConfig."""
    config = MagicMock()
    config.auth_config = MagicMock(return_value={"enabled": True})
    return config


@pytest.fixture
def mock_auth_backend():
    """Create a mock BaseAuth backend."""
    backend = MagicMock()
    backend.authenticate = MagicMock(return_value={"user_id": "test-user"})
    return backend


@pytest.fixture
def mock_authz():
    """Create a mock AuthorizationBackend."""
    authz = MagicMock()
    authz.authorize = AsyncMock(return_value=True)
    return authz


class TestRequirePermissionInit:
    """Test RequirePermission initialization."""

    def test_init_with_resource_and_action(self):
        """Test initialization with resource and action."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        perm = RequirePermission("graph", "invoke")

        assert perm.resource == "graph"
        assert perm.action == "invoke"
        assert perm.extract_resource_id_fn is None

    def test_init_with_custom_extractor(self):
        """Test initialization with custom resource ID extractor."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        def custom_extractor(request):
            return request.query_params.get("resource_id")

        perm = RequirePermission("store", "read", extract_resource_id=custom_extractor)

        assert perm.resource == "store"
        assert perm.action == "read"
        assert perm.extract_resource_id_fn is custom_extractor

    def test_init_different_resources(self):
        """Test initialization with different resource types."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        for resource in ["graph", "checkpointer", "store", "agent"]:
            perm = RequirePermission(resource, "read")
            assert perm.resource == resource

    def test_init_different_actions(self):
        """Test initialization with different action types."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        for action in ["invoke", "read", "write", "delete", "stream", "create"]:
            perm = RequirePermission("resource", action)
            assert perm.action == action


class TestRequirePermissionCall:
    """Test RequirePermission __call__ method."""

    @pytest.mark.asyncio
    async def test_call_with_auth_not_configured(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test __call__ when auth is not configured."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        # Configure mocks
        mock_config.auth_config = MagicMock(return_value=None)

        perm = RequirePermission("graph", "invoke")

        result = await perm(
            mock_request, mock_response, mock_credential, mock_config, mock_auth_backend, mock_authz
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_call_with_valid_auth_and_authz(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test __call__ with valid authentication and authorization."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        perm = RequirePermission("graph", "invoke")

        result = await perm(
            mock_request, mock_response, mock_credential, mock_config, mock_auth_backend, mock_authz
        )

        assert result == {"user_id": "test-user"}
        mock_auth_backend.authenticate.assert_called_once()
        mock_authz.authorize.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_auth_backend_not_configured(
        self, mock_request, mock_response, mock_credential, mock_config
    ):
        """Test __call__ when auth backend is not configured."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        # Set auth_config to return something truthy
        mock_config.auth_config = MagicMock(return_value={"enabled": True})

        perm = RequirePermission("graph", "invoke")

        with patch("agentflow_cli.src.app.core.auth.permissions.logger") as mock_logger:
            result = await perm(
                mock_request,
                mock_response,
                mock_credential,
                mock_config,
                None,
                MagicMock(authorize=AsyncMock(return_value=True)),
            )

        assert result == {}
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_call_authorization_failed(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test __call__ when authorization fails."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        # Configure authorization to fail
        mock_authz.authorize = AsyncMock(return_value=False)

        perm = RequirePermission("graph", "invoke")

        with pytest.raises(HTTPException) as exc_info:
            await perm(
                mock_request,
                mock_response,
                mock_credential,
                mock_config,
                mock_auth_backend,
                mock_authz,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_call_authentication_missing_user_id(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test __call__ when authentication returns data without user_id."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        # Configure authentication to return data without user_id
        mock_auth_backend.authenticate = MagicMock(return_value={"other_field": "value"})

        perm = RequirePermission("graph", "invoke")

        with patch("agentflow_cli.src.app.core.auth.permissions.logger") as mock_logger:
            result = await perm(
                mock_request,
                mock_response,
                mock_credential,
                mock_config,
                mock_auth_backend,
                mock_authz,
            )

            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_call_with_custom_resource_id_extractor(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test __call__ with custom resource ID extractor function."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        def custom_extractor(request):
            return "custom-resource-id"

        perm = RequirePermission("graph", "invoke", extract_resource_id=custom_extractor)

        result = await perm(
            mock_request, mock_response, mock_credential, mock_config, mock_auth_backend, mock_authz
        )

        # Verify authorize was called with the custom resource ID
        mock_authz.authorize.assert_called_once()
        call_args = mock_authz.authorize.call_args
        assert call_args[1]["resource_id"] == "custom-resource-id"


class TestExtractResourceIdFromPath:
    """Test _extract_resource_id_from_path method."""

    def test_extract_thread_id_from_path(self, mock_request):
        """Test extracting thread_id from path parameters."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"thread_id": "thread-123"}

        perm = RequirePermission("checkpointer", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        assert resource_id == "thread-123"

    def test_extract_memory_id_from_path(self, mock_request):
        """Test extracting memory_id from path parameters."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"memory_id": "mem-456"}

        perm = RequirePermission("store", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        assert resource_id == "mem-456"

    def test_extract_namespace_from_path(self, mock_request):
        """Test extracting namespace from path parameters."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"namespace": "my-namespace"}

        perm = RequirePermission("graph", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        assert resource_id == "my-namespace"

    def test_extract_returns_none_when_no_match(self, mock_request):
        """Test that extract returns None when no matching parameter found."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"other_param": "value"}

        perm = RequirePermission("graph", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        assert resource_id is None

    def test_extract_returns_first_match(self, mock_request):
        """Test that extract returns first matching parameter."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"thread_id": "thread-789", "memory_id": "mem-999"}

        perm = RequirePermission("graph", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        # Should return thread_id as it's checked first
        assert resource_id == "thread-789"

    def test_extract_converts_to_string(self, mock_request):
        """Test that extract converts resource ID to string."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"thread_id": 123}

        perm = RequirePermission("checkpointer", "read")
        resource_id = perm._extract_resource_id_from_path(mock_request)

        assert resource_id == "123"
        assert isinstance(resource_id, str)


class TestRequirePermissionIntegration:
    """Integration tests for RequirePermission."""

    @pytest.mark.asyncio
    async def test_full_flow_with_auth_configured_and_authorized(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test complete flow with auth configured and user authorized."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_request.path_params = {"thread_id": "test-thread"}
        mock_config.auth_config = MagicMock(return_value={"enabled": True})
        mock_auth_backend.authenticate = MagicMock(
            return_value={"user_id": "user-123", "role": "admin"}
        )
        mock_authz.authorize = AsyncMock(return_value=True)

        perm = RequirePermission("checkpointer", "read")

        result = await perm(
            mock_request, mock_response, mock_credential, mock_config, mock_auth_backend, mock_authz
        )

        assert result == {"user_id": "user-123", "role": "admin"}
        mock_authz.authorize.assert_called_once_with(
            {"user_id": "user-123", "role": "admin"},
            "checkpointer",
            "read",
            resource_id="test-thread",
        )

    @pytest.mark.asyncio
    async def test_full_flow_auth_not_configured_skips_checks(
        self,
        mock_request,
        mock_response,
        mock_credential,
        mock_config,
        mock_auth_backend,
        mock_authz,
    ):
        """Test that when auth not configured, no auth/authz checks are performed."""
        from agentflow_cli.src.app.core.auth.permissions import RequirePermission

        mock_config.auth_config = MagicMock(return_value=None)

        perm = RequirePermission("graph", "invoke")

        result = await perm(
            mock_request, mock_response, mock_credential, mock_config, mock_auth_backend, mock_authz
        )

        assert result == {}
        # Verify authenticate and authorize were NOT called
        mock_auth_backend.authenticate.assert_not_called()
        mock_authz.authorize.assert_not_called()
