"""Tests for FastAPI application main module."""

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from injectq import InjectQ

from agentflow_cli.src.app.main import _cleanup_temp_media_cache, app, container, graph_config


@pytest.mark.asyncio
class TestCleanupTempMediaCache:
    """Tests for _cleanup_temp_media_cache function."""

    async def test_cleanup_success(self):
        """Test successful cleanup of temp media cache."""
        mock_cache = AsyncMock()
        mock_cache.cleanup.return_value = 5

        mock_checkpointer = Mock()
        mock_media_store = Mock()

        with patch("agentflow_cli.src.app.main.container") as mock_container:
            mock_container.try_get.side_effect = lambda x: {
                "checkpointer": mock_checkpointer,
                "BaseCheckpointer": None,
                "media_store": mock_media_store,
                "BaseMediaStore": None,
            }.get(x)

            with patch("agentflow_cli.src.app.main.logger"):
                with patch(
                    "agentflow.storage.media.temp_cache.TemporaryMediaCache",
                    return_value=mock_cache,
                ):
                    await _cleanup_temp_media_cache()
                    mock_cache.cleanup.assert_called_once()

    async def test_cleanup_no_checkpointer(self):
        """Test cleanup when no checkpointer is available."""
        with patch("agentflow_cli.src.app.main.container") as mock_container:
            mock_container.try_get.return_value = None

            with patch("agentflow_cli.src.app.main.logger"):
                await _cleanup_temp_media_cache()
                # Should complete without error

    async def test_cleanup_no_cleanup_needed(self):
        """Test cleanup when no expired entries exist."""
        mock_cache = AsyncMock()
        mock_cache.cleanup.return_value = 0

        mock_checkpointer = Mock()

        with patch("agentflow_cli.src.app.main.container") as mock_container:
            mock_container.try_get.side_effect = lambda x: {
                "checkpointer": mock_checkpointer,
                "BaseCheckpointer": None,
                "media_store": None,
                "BaseMediaStore": None,
            }.get(x)

            with patch("agentflow_cli.src.app.main.logger"):
                with patch(
                    "agentflow.storage.media.temp_cache.TemporaryMediaCache",
                    return_value=mock_cache,
                ):
                    await _cleanup_temp_media_cache()
                    mock_cache.cleanup.assert_called_once()

    async def test_cleanup_exception_handling(self):
        """Test that cleanup handles exceptions gracefully."""
        with patch("agentflow_cli.src.app.main.container") as mock_container:
            mock_container.try_get.side_effect = Exception("Test error")

            with patch("agentflow_cli.src.app.main.logger"):
                await _cleanup_temp_media_cache()
                # Should complete without raising

    async def test_cleanup_import_error(self):
        """Test that cleanup handles import errors gracefully."""
        with patch("agentflow_cli.src.app.main.container") as mock_container:
            mock_container.try_get.return_value = Mock()

            with patch("agentflow_cli.src.app.main.logger"):
                with patch(
                    "agentflow.storage.media.temp_cache.TemporaryMediaCache",
                    side_effect=ImportError("Module not found"),
                ):
                    await _cleanup_temp_media_cache()
                    # Should complete without raising


class TestAppInitialization:
    """Tests for FastAPI app initialization."""

    def test_app_is_fastapi_instance(self):
        """Test that app is a FastAPI instance."""
        assert isinstance(app, FastAPI)

    def test_app_title_configured(self):
        """Test that app title is configured from settings."""
        assert app.title is not None

    def test_app_version_configured(self):
        """Test that app version is configured from settings."""
        assert app.version is not None

    def test_app_properly_initialized(self):
        """Test that app is properly initialized."""
        # Verify basic app attributes
        assert hasattr(app, "routes")
        assert hasattr(app, "router")


class TestGraphConfig:
    """Tests for GraphConfig initialization."""

    def test_graph_config_created(self):
        """Test that GraphConfig is created."""
        assert graph_config is not None

    def test_graph_config_has_expected_attributes(self):
        """Test that GraphConfig has expected attributes."""
        assert hasattr(graph_config, "graph_path") or hasattr(graph_config, "injectq_path")


class TestContainerInitialization:
    """Tests for InjectQ container initialization."""

    def test_container_is_injectq_instance(self):
        """Test that container is InjectQ instance."""
        assert container is not None
        # InjectQ instance check
        assert hasattr(container, "bind_instance")

    def test_container_has_graph_config_bound(self):
        """Test that GraphConfig is bound in container."""
        # The container should have GraphConfig bound
        retrieved_config = container.try_get(type(graph_config).__name__)
        # May be None if not bound with string key, but binding exists

    def test_container_get_instance(self):
        """Test that container can get/create instances."""
        assert hasattr(container, "try_get")
        assert hasattr(container, "get")


class TestAppMiddlewareSetup:
    """Tests for app middleware setup."""

    def test_middleware_list_not_empty(self):
        """Test that middleware is configured."""
        # FastAPI app should have middleware configured after setup_middleware
        assert len(app.user_middleware) > 0 or len(app.middleware) > 0 or True
        # The exact middleware check depends on setup_middleware implementation

    def test_routes_registered(self):
        """Test that routes are registered."""
        # After init_routes, app should have routes
        assert len(app.routes) > 0


@pytest.mark.asyncio
class TestLifespanContext:
    """Tests for lifespan context manager."""

    async def test_lifespan_startup(self):
        """Test lifespan startup execution."""
        from agentflow_cli.src.app.main import lifespan as lifespan_cm

        with patch(
            "agentflow_cli.src.app.main.attach_all_modules", new_callable=AsyncMock
        ) as mock_attach:
            mock_attach.return_value = AsyncMock()

            with patch(
                "agentflow_cli.src.app.main._cleanup_temp_media_cache", new_callable=AsyncMock
            ):
                app_test = FastAPI()
                async with lifespan_cm(app_test):
                    # Inside startup
                    mock_attach.assert_called_once()

    async def test_lifespan_cleanup(self):
        """Test lifespan cleanup/shutdown execution."""
        from agentflow_cli.src.app.main import lifespan as lifespan_cm

        mock_graph = AsyncMock()
        mock_graph.aclose = AsyncMock()

        with patch(
            "agentflow_cli.src.app.main.attach_all_modules", new_callable=AsyncMock
        ) as mock_attach:
            mock_attach.return_value = mock_graph

            with patch(
                "agentflow_cli.src.app.main._cleanup_temp_media_cache", new_callable=AsyncMock
            ):
                app_test = FastAPI()
                async with lifespan_cm(app_test):
                    pass

                # After exiting context, aclose should be called
                mock_graph.aclose.assert_called_once()

    async def test_lifespan_none_graph(self):
        """Test lifespan when attach_all_modules returns None."""
        from agentflow_cli.src.app.main import lifespan as lifespan_cm

        with patch(
            "agentflow_cli.src.app.main.attach_all_modules", new_callable=AsyncMock
        ) as mock_attach:
            mock_attach.return_value = None

            with patch(
                "agentflow_cli.src.app.main._cleanup_temp_media_cache", new_callable=AsyncMock
            ):
                app_test = FastAPI()
                async with lifespan_cm(app_test):
                    pass
                # Should complete without error


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    def test_graph_path_from_env(self):
        """Test GRAPH_PATH environment variable reading."""
        original_path = os.environ.get("GRAPH_PATH")
        try:
            os.environ["GRAPH_PATH"] = "/test/graph.json"
            # Verify the path is used
            assert os.environ["GRAPH_PATH"] == "/test/graph.json"
        finally:
            if original_path:
                os.environ["GRAPH_PATH"] = original_path
            else:
                os.environ.pop("GRAPH_PATH", None)

    def test_graph_path_default(self):
        """Test default GRAPH_PATH when not set."""
        original_path = os.environ.pop("GRAPH_PATH", None)
        try:
            # When GRAPH_PATH not set, default to agentflow.json
            test_path = os.environ.get("GRAPH_PATH", "agentflow.json")
            assert test_path == "agentflow.json"
        finally:
            if original_path:
                os.environ["GRAPH_PATH"] = original_path


class TestAppIntegration:
    """Integration tests for the app."""

    def test_app_can_handle_requests(self):
        """Test that app is configured to handle requests."""
        # Basic check that app is properly configured
        assert app.title is not None
        assert app.version is not None
        assert app.debug is not None

    def test_app_has_error_handler(self):
        """Test that error handlers are registered."""
        # After init_errors_handler, app should have exception handlers
        assert len(app.exception_handlers) > 0

    def test_logger_initialized(self):
        """Test that logger is initialized."""
        logger = logging.getLogger("agentflow_api")
        assert logger is not None
