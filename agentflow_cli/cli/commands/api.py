"""API server command implementation."""

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import uvicorn
from dotenv import load_dotenv

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_HOST,
    DEFAULT_PLAYGROUND_URL,
    DEFAULT_PORT,
)
from agentflow_cli.cli.core.config import ConfigManager
from agentflow_cli.cli.core.validation import validate_cli_options
from agentflow_cli.cli.exceptions import ConfigurationError, ServerError


class APICommand(BaseCommand):
    """Command to start the Pyagenity API server."""

    _PLAYGROUND_WAIT_TIMEOUT_SECONDS = 30.0
    _PLAYGROUND_WAIT_INTERVAL_SECONDS = 0.25

    def execute(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        reload: bool = True,
        open_playground: bool = False,
        playground_url: str = DEFAULT_PLAYGROUND_URL,
        **kwargs: Any,
    ) -> int:
        """Execute the API server command.

        Args:
            config: Path to config file
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload
            open_playground: Open the hosted playground after the API becomes reachable
            playground_url: Hosted playground base URL
            **kwargs: Additional arguments

        Returns:
            Exit code
        """
        try:
            # Print banner
            self.output.print_banner(
                "API (development)",
                "Starting development server via Uvicorn. Not for production use.",
            )

            # Validate inputs
            validated_options = validate_cli_options(host, port, config)

            # Load configuration
            config_manager = ConfigManager()
            actual_config_path = config_manager.find_config_file(validated_options["config"])
            # Load and validate config
            config_manager.load_config(str(actual_config_path))

            # Load environment file if specified
            env_file_path = config_manager.resolve_env_file()
            if env_file_path:
                self.logger.info("Loading environment from: %s", env_file_path)
                load_dotenv(env_file_path)
            else:
                # Load default .env if it exists
                load_dotenv()

            # Set environment variables
            os.environ["GRAPH_PATH"] = str(actual_config_path)

            # Add project root to sys.path for importing graph modules
            sys.path.insert(0, str(actual_config_path.parent))

            # Ensure we're using the correct module path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            self.logger.info(
                "Starting API with config: %s, host: %s, port: %d",
                actual_config_path,
                validated_options["host"],
                validated_options["port"],
            )

            if open_playground:
                self._schedule_playground_launch(
                    host=validated_options["host"],
                    port=validated_options["port"],
                    playground_base_url=playground_url,
                )

            # Start the server
            uvicorn.run(
                "agentflow_cli.src.app.main:app",
                host=validated_options["host"],
                port=validated_options["port"],
                reload=reload,
                workers=1,
            )

            return 0

        except (ConfigurationError, ServerError) as e:
            return self.handle_error(e)
        except Exception as e:
            server_error = ServerError(
                f"Failed to start API server: {e}",
                host=host,
                port=port,
            )
            return self.handle_error(server_error)

    def _schedule_playground_launch(
        self,
        host: str,
        port: int,
        playground_base_url: str,
    ) -> None:
        browser_host = self._normalize_browser_host(host)
        launch_url = self._build_playground_url(browser_host, port, playground_base_url)
        self.output.info(
            f"Playground will open at {launch_url} when the API is ready.",
            emoji=False,
        )
        launch_thread = threading.Thread(
            target=self._open_playground_when_ready,
            args=(launch_url, browser_host, port),
            daemon=True,
            name="agentflow-playground-launcher",
        )
        launch_thread.start()

    def _open_playground_when_ready(
        self,
        launch_url: str,
        host: str,
        port: int,
    ) -> None:
        if not self._wait_for_server(host, port):
            self.logger.warning(
                "API server did not become reachable in time. Open the playground manually: %s",
                launch_url,
            )
            return

        opened = webbrowser.open_new_tab(launch_url)
        if opened:
            self.logger.info("Opened playground URL: %s", launch_url)
            return

        self.logger.warning(
            "Browser launch returned false. Open the playground manually: %s",
            launch_url,
        )

    def _wait_for_server(
        self,
        host: str,
        port: int,
    ) -> bool:
        deadline = time.monotonic() + self._PLAYGROUND_WAIT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return True
            except OSError:
                time.sleep(self._PLAYGROUND_WAIT_INTERVAL_SECONDS)

        return False

    def _build_playground_url(
        self,
        host: str,
        port: int,
        playground_base_url: str,
    ) -> str:
        backend_host = host
        if ":" in backend_host and not backend_host.startswith("["):
            backend_host = f"[{backend_host}]"

        backend_url = f"http://{backend_host}:{port}"
        return f"{playground_base_url}?{urlencode({'backendUrl': backend_url})}"

    def _normalize_browser_host(self, host: str) -> str:
        if host in {"0.0.0.0", "::", "[::]", ""}:
            return "127.0.0.1"
        if host.startswith("[") and host.endswith("]"):
            return host[1:-1]
        return host
