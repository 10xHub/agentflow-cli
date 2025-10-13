"""Professional Pyagenity CLI main entry point."""

import sys

import typer
from dotenv import load_dotenv

from agentflow_cli.cli.commands.api import APICommand
from agentflow_cli.cli.commands.build import BuildCommand
from agentflow_cli.cli.commands.init import InitCommand
from agentflow_cli.cli.commands.version import VersionCommand
from agentflow_cli.cli.constants import DEFAULT_CONFIG_FILE, DEFAULT_HOST, DEFAULT_PORT
from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.exceptions import PyagenityCLIError
from agentflow_cli.cli.logger import setup_cli_logging


# Load environment variables
load_dotenv()

# Create the main Typer app
app = typer.Typer(
    name="agentflow",
    help=(
        "Pyagenity API CLI - Professional tool for managing Pyagenity API "
        "servers and configurations"
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

# Initialize global output formatter
output = OutputFormatter()


def handle_exception(e: Exception) -> int:
    """Handle exceptions consistently across all commands.

    Args:
        e: Exception that occurred

    Returns:
        Appropriate exit code
    """
    if isinstance(e, PyagenityCLIError):
        output.error(e.message)
        return e.exit_code

    output.error(f"Unexpected error: {e}")
    return 1


@app.command()
def api(
    config: str = typer.Option(
        DEFAULT_CONFIG_FILE,
        "--config",
        "-c",
        help="Path to config file",
    ),
    host: str = typer.Option(
        DEFAULT_HOST,
        "--host",
        "-H",
        help="Host to run the API on (default: 0.0.0.0, binds to all interfaces; "
        "use 127.0.0.1 for localhost only)",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to run the API on",
    ),
    reload: bool = typer.Option(
        True,
        "--reload/--no-reload",
        help="Enable auto-reload for development",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
) -> None:
    """Start the Pyagenity API server."""
    # Setup logging
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = APICommand(output)
        exit_code = command.execute(
            config=config,
            host=host,
            port=port,
            reload=reload,
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command()
def version(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
) -> None:
    """Show the CLI version."""
    # Setup logging
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = VersionCommand(output)
        exit_code = command.execute()
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command()
def init(
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Directory to initialize config and graph files in",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files if they exist",
    ),
    prod: bool = typer.Option(
        False,
        "--prod",
        help=(
            "Initialize production-ready project (adds pyproject.toml and .pre-commit-config.yaml)"
        ),
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
) -> None:
    """Initialize default config and graph files (agentflow.json and graph/react.py)."""
    # Setup logging
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = InitCommand(output)
        exit_code = command.execute(path=path, force=force, prod=prod)
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command()
def build(
    output_file: str = typer.Option(
        "Dockerfile",
        "--output",
        "-o",
        help="Output Dockerfile path",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing Dockerfile",
    ),
    python_version: str = typer.Option(
        "3.13",
        "--python-version",
        help="Python version to use",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to expose in the container",
    ),
    docker_compose: bool = typer.Option(
        False,
        "--docker-compose/--no-docker-compose",
        help="Also generate docker-compose.yml and omit CMD in Dockerfile",
    ),
    service_name: str = typer.Option(
        "agentflow-cli",
        "--service-name",
        help="Service name to use in docker-compose.yml (if generated)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
) -> None:
    """Generate a Dockerfile for the Pyagenity API application."""
    # Setup logging
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = BuildCommand(output)
        exit_code = command.execute(
            output_file=output_file,
            force=force,
            python_version=python_version,
            port=port,
            docker_compose=docker_compose,
            service_name=service_name,
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


def main() -> None:
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        output.warning("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        sys.exit(handle_exception(e))


if __name__ == "__main__":
    main()
