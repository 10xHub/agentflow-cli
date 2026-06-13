"""Professional Agentflow CLI main entry point."""

import sys

import typer
from dotenv import load_dotenv

from agentflow_cli.cli.commands.api import APICommand
from agentflow_cli.cli.commands.build import BuildCommand
from agentflow_cli.cli.commands.eval import EvalCommand
from agentflow_cli.cli.commands.init import InitCommand
from agentflow_cli.cli.commands.skills import SkillsCommand
from agentflow_cli.cli.commands.test import TestCommand
from agentflow_cli.cli.commands.version import VersionCommand
from agentflow_cli.cli.constants import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.exceptions import AgentflowCLIError
from agentflow_cli.cli.logger import setup_cli_logging


# Load environment variables
load_dotenv()

# Create the main Typer app
app = typer.Typer(
    name="agentflow",
    help=(
        "Agentflow API CLI - Professional tool for managing Agentflow API "
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
    if isinstance(e, AgentflowCLIError):
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
        help="Host to run the API on (default: 127.0.0.1, localhost only; "
        "use 0.0.0.0 to bind all interfaces)",
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
    """Start the Agentflow API server."""
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
def play(
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
        help=(
            "Host to run the API on for the local playground session "
            "(use 127.0.0.1 for localhost only)"
        ),
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
    """Start the API server and open the hosted playground."""
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = APICommand(output)
        exit_code = command.execute(
            config=config,
            host=host,
            port=port,
            reload=reload,
            open_playground=True,
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
        help="Directory to initialize the agent project in",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing files if they exist",
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
    """Interactively initialize a new agent project."""
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = InitCommand(output)
        exit_code = command.execute(path=path, force=force)
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
    """Generate a Dockerfile for the Agentflow API application."""
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


@app.command()
def skills(
    agent: str | None = typer.Option(
        None,
        "--agent",
        "-a",
        help="Target agent: codex, claude, github, or menu number 1, 2, 3",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Project directory where the skills should be installed",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite the existing installed Agentflow skill directory",
    ),
    all_agents: bool = typer.Option(
        False,
        "--all",
        help="Install skills for every supported agent",
    ),
    list_agents: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List supported agents and exit",
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
    """Install bundled Agentflow skills for Codex, Claude, or GitHub."""
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = SkillsCommand(output)
        exit_code = command.execute(
            agent=agent,
            path=path,
            force=force,
            all_agents=all_agents,
            list_agents=list_agents,
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def test(
    ctx: typer.Context,
    path: str | None = typer.Argument(
        None, help="Path to tests directory or file (omit to let pytest auto-discover)"
    ),
    coverage: bool = typer.Option(False, "--coverage", "-C", help="Run with coverage"),
    html: bool = typer.Option(
        False, "--html", help="Open HTML coverage report after run (requires --coverage)"
    ),
    keyword: str | None = typer.Option(None, "-k", help="Only run tests matching this expression"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
) -> None:
    """Run project tests with pytest.

    Any arguments after -- are forwarded verbatim to pytest.
    """
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = TestCommand(output)
        exit_code = command.execute(
            path=path,
            coverage=coverage,
            html=html,
            keyword=keyword,
            verbose=verbose,
            quiet=quiet,
            extra_args=tuple(ctx.args),
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command(name="eval")
def eval_cmd(
    target: str | None = typer.Argument(
        None,
        help="File or directory to evaluate (default: evals/ from agentflow.json or cwd)",
    ),
    output_dir: str = typer.Option(
        "eval_reports",
        "--output",
        "-o",
        help="Directory for generated report files",
    ),
    no_report: bool = typer.Option(
        False,
        "--no-report",
        help="Skip file report generation (console summary only)",
    ),
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        "-t",
        help="Fail if overall pass rate is below this value (0.0-1.0)",
    ),
    open_report: bool = typer.Option(
        False,
        "--open",
        help="Open the HTML report in the default browser after the run",
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        "-p",
        help="Collect all cases from all files into a flat pool and run them concurrently",
    ),
    max_concurrency: int = typer.Option(
        4,
        "--max-concurrency",
        "-c",
        help="Max cases running concurrently when --parallel is set (global semaphore)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
) -> None:
    """Run agent evaluations.

    Discovers *_eval.py / eval_*.py files in the target directory (default: evals/).
    Collects all cases from all files into a flat pool, then runs them under a single
    event loop throttled by --max-concurrency.  Always generates HTML + JSON reports
    in eval_reports/ unless --no-report is set.

    Each eval file must expose one of:
      get_eval_set() + get_eval_config() # CLI loads agent from agentflow.json
      EVAL_CONFIG + get_eval_set()       # same, config as a constant
      any function returning EvalSet     # auto-discovered, pytest-style
    """
    setup_cli_logging(verbose=verbose, quiet=quiet)

    try:
        command = EvalCommand(output)
        exit_code = command.execute(
            target=target,
            output_dir=output_dir,
            no_report=no_report,
            threshold=threshold,
            open_report=open_report,
            parallel=parallel,
            max_concurrency=max_concurrency,
            verbose=verbose,
            quiet=quiet,
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
