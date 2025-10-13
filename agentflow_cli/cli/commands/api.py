"""API server command implementation."""

import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv

from agentflow_cli.cli.commands import BaseCommand
from agentflow_cli.cli.constants import DEFAULT_CONFIG_FILE, DEFAULT_HOST, DEFAULT_PORT
from agentflow_cli.cli.core.config import ConfigManager
from agentflow_cli.cli.core.validation import validate_cli_options
from agentflow_cli.cli.exceptions import ConfigurationError, ServerError


class APICommand(BaseCommand):
    """Command to start the Pyagenity API server."""

    def execute(
        self,
        config: str = DEFAULT_CONFIG_FILE,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        reload: bool = True,
        **kwargs: Any,
    ) -> int:
        """Execute the API server command.

        Args:
            config: Path to config file
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload
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

            # Ensure we're using the correct module path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            self.logger.info(
                "Starting API with config: %s, host: %s, port: %d",
                actual_config_path,
                validated_options["host"],
                validated_options["port"],
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
