"""Agentflow CLI entry point and lightweight command registry."""

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import typer

from agentflow_cli.cli.capabilities import ColorMode, OutputFormat, ProgressMode
from agentflow_cli.cli.constants import (
    CLI_VERSION,
    DEFAULT_CONFIG_FILE,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from agentflow_cli.cli.context import CLIContext
from agentflow_cli.cli.core.output import OutputFormatter
from agentflow_cli.cli.exceptions import AgentflowCLIError, ConfigurationError, DependencyError
from agentflow_cli.cli.logger import setup_cli_logging
from agentflow_cli.cli.user_config import UserConfigStore, parse_config_value


def _lazy_command(module_name: str, class_name: str) -> type:
    """Create a compatibility-preserving lazy command adapter.

    Only the selected command's implementation and heavy dependencies are imported.
    Keeping these class-shaped adapters also preserves the public monkeypatch surface
    used by downstream tests and integrations.
    """

    class LazyCommand:
        def __init__(self, output: OutputFormatter | None = None) -> None:
            self.output = output

        def execute(self, *args: Any, **kwargs: Any) -> int:
            try:
                module = importlib.import_module(module_name)
            except ImportError as exc:
                feature = class_name.removesuffix("Command").lower()
                raise DependencyError(
                    f"The {feature} command could not load its required dependencies: {exc}",
                    hints=(
                        "Run `agentflow doctor` to inspect installed package compatibility.",
                        "Upgrade with `python -m pip install --upgrade "
                        '"10xscale-agentflow>=0.9,<2"`.',
                    ),
                ) from exc
            implementation = getattr(module, class_name)
            return implementation(self.output).execute(*args, **kwargs)

    LazyCommand.__name__ = class_name
    LazyCommand.__qualname__ = class_name
    return LazyCommand


APICommand = _lazy_command("agentflow_cli.cli.commands.api", "APICommand")
BuildCommand = _lazy_command("agentflow_cli.cli.commands.build", "BuildCommand")
EvalCommand = _lazy_command("agentflow_cli.cli.commands.eval", "EvalCommand")
DoctorCommand = _lazy_command("agentflow_cli.cli.commands.doctor", "DoctorCommand")
InitCommand = _lazy_command("agentflow_cli.cli.commands.init", "InitCommand")
SkillsCommand = _lazy_command("agentflow_cli.cli.commands.skills", "SkillsCommand")
TestCommand = _lazy_command("agentflow_cli.cli.commands.test", "TestCommand")
VersionCommand = _lazy_command("agentflow_cli.cli.commands.version", "VersionCommand")

# Create the main Typer app
app = typer.Typer(
    name="agentflow",
    help="Build, run, test, and evaluate production-ready Agentflow agents.",
    epilog=(
        "Examples:\n"
        "  agentflow init\n"
        "  agentflow dev\n"
        "  agentflow test --coverage\n"
        "  agentflow eval --parallel"
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
config_app = typer.Typer(
    name="config",
    help="Inspect and manage user-level Agentflow CLI preferences.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config", rich_help_panel="Manage")

# Initialize global output formatter
output = OutputFormatter()


@app.callback(invoke_without_command=True)
def root(  # noqa: PLR0913
    ctx: typer.Context,
    output_format: OutputFormat | None = typer.Option(
        None,
        "--format",
        help="Output format: human, plain, json, or jsonl.",
        rich_help_panel="Global output",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit versioned JSON output; shorthand for --format json.",
        rich_help_panel="Global output",
    ),
    color: ColorMode | None = typer.Option(
        None,
        "--color",
        help="Color policy: auto, always, or never.",
        rich_help_panel="Global output",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable ANSI color; shorthand for --color never.",
        rich_help_panel="Global output",
    ),
    progress: ProgressMode | None = typer.Option(
        None,
        "--progress",
        help="Progress mode: auto, tty, plain, json, or quiet.",
        rich_help_panel="Global output",
    ),
    animation: bool | None = typer.Option(
        None,
        "--animation/--no-animation",
        help="Enable or disable decorative command animation.",
        rich_help_panel="Global output",
    ),
    cwd: Path | None = typer.Option(
        None,
        "--cwd",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Run as if Agentflow was started in this directory.",
        rich_help_panel="Global context",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase diagnostic verbosity; repeat for more detail.",
        rich_help_panel="Diagnostics",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress informational, progress, and success output.",
        rich_help_panel="Global output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug diagnostics.",
        rich_help_panel="Diagnostics",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Accept recommended defaults for supported workflows.",
        rich_help_panel="Global context",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Never prompt for input.",
        rich_help_panel="Global context",
    ),
    version_flag: bool = typer.Option(
        False,
        "--version",
        "-V",
        is_eager=True,
        help="Show the CLI version and exit.",
        rich_help_panel="Global options",
    ),
) -> None:
    """Resolve invocation-wide terminal, logging, and working-directory policy."""
    if cwd is not None:
        os.chdir(cwd)

    preferences = UserConfigStore()
    try:
        if json_output and output_format not in {None, OutputFormat.JSON}:
            raise typer.BadParameter("--json cannot be combined with a different --format.")
        if no_color and color not in {None, ColorMode.NEVER}:
            raise typer.BadParameter("--no-color cannot be combined with a different --color.")
        if animation is not None and progress is not None:
            expected = ProgressMode.TTY if animation else ProgressMode.PLAIN
            if progress != expected:
                raise typer.BadParameter(
                    "--animation/--no-animation conflicts with the selected --progress mode."
                )
        resolved_format = output_format or OutputFormat(
            preferences.get("output.format", OutputFormat.HUMAN)
        )
        resolved_color = color or ColorMode(preferences.get("output.color", ColorMode.AUTO))
        resolved_progress = progress or ProgressMode(
            preferences.get("output.progress", ProgressMode.AUTO)
        )
        if json_output:
            resolved_format = OutputFormat.JSON
        if no_color:
            resolved_color = ColorMode.NEVER
        if animation is not None:
            resolved_progress = ProgressMode.TTY if animation else ProgressMode.PLAIN
    except (ConfigurationError, ValueError) as exc:
        if ctx.invoked_subcommand != "config":
            raise typer.BadParameter(
                f"Invalid user output configuration: {exc}. Run `agentflow config validate`."
            ) from exc
        resolved_format = output_format or OutputFormat.HUMAN
        resolved_color = color or ColorMode.AUTO
        resolved_progress = progress or ProgressMode.AUTO

    output.configure(
        output_format=resolved_format,
        color_mode=resolved_color,
        progress_mode=resolved_progress,
        quiet=quiet,
    )
    setup_cli_logging(verbose=verbose > 0 or debug, quiet=quiet)
    ctx.obj = CLIContext.create(
        capabilities=output.capabilities,
        cwd=Path.cwd(),
        verbosity=verbose,
        quiet=quiet,
        debug=debug,
        yes=yes,
        non_interactive=non_interactive,
    )

    if version_flag:
        typer.echo(CLI_VERSION)
        raise typer.Exit()


@config_app.command("path")
def config_path() -> None:
    """Print the user configuration file path."""
    typer.echo(UserConfigStore().path)


@config_app.command("list")
def config_list() -> None:
    """List all user-level CLI preferences."""
    store = UserConfigStore()
    try:
        values = store.load()
    except ConfigurationError as exc:
        raise typer.Exit(handle_exception(exc)) from exc
    output.print_key_value_pairs(_flatten_mapping(values), title="User configuration")


@config_app.command("get")
def config_get(key: str = typer.Argument(..., help="Dot-separated preference key.")) -> None:
    """Read one user-level CLI preference."""
    store = UserConfigStore()
    try:
        value = store.get(key)
    except ConfigurationError as exc:
        raise typer.Exit(handle_exception(exc)) from exc
    if value is None:
        raise typer.Exit(
            handle_exception(
                ConfigurationError(
                    f"Configuration key '{key}' is not set.",
                    config_path=str(store.path),
                )
            )
        )
    if isinstance(value, dict | list):
        typer.echo(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        typer.echo(value)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dot-separated preference key."),
    value: str = typer.Argument(..., help="JSON value or plain string."),
) -> None:
    """Set one user-level CLI preference."""
    store = UserConfigStore()
    try:
        store.set(key, parse_config_value(value))
    except ConfigurationError as exc:
        raise typer.Exit(handle_exception(exc)) from exc
    output.success(f"Set {key} in {store.path}")


@config_app.command("unset")
def config_unset(key: str = typer.Argument(..., help="Dot-separated preference key.")) -> None:
    """Remove one user-level CLI preference."""
    store = UserConfigStore()
    try:
        removed = store.unset(key)
    except ConfigurationError as exc:
        raise typer.Exit(handle_exception(exc)) from exc
    if not removed:
        raise typer.Exit(
            handle_exception(
                ConfigurationError(
                    f"Configuration key '{key}' is not set.",
                    config_path=str(store.path),
                )
            )
        )
    output.success(f"Removed {key} from {store.path}")


@config_app.command("validate")
def config_validate() -> None:
    """Validate the user configuration and supported output preferences."""
    store = UserConfigStore()
    try:
        store.load()
        OutputFormat(store.get("output.format", OutputFormat.HUMAN))
        ColorMode(store.get("output.color", ColorMode.AUTO))
        ProgressMode(store.get("output.progress", ProgressMode.AUTO))
    except (ConfigurationError, ValueError) as exc:
        raise typer.Exit(handle_exception(ConfigurationError(str(exc)))) from exc
    output.success(f"User configuration is valid: {store.path}")


def _flatten_mapping(
    values: dict[str, Any],
    *,
    prefix: str = "",
) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in values.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(_flatten_mapping(value, prefix=dotted))
        else:
            flattened[dotted] = value
    return flattened


def _configure_command(*, verbose: bool, quiet: bool) -> None:
    """Apply legacy per-command flags without overriding root output choices."""
    setup_cli_logging(verbose=verbose, quiet=quiet)
    if quiet:
        output.configure(quiet=True)


def handle_exception(e: Exception) -> int:
    """Handle exceptions consistently across all commands.

    Args:
        e: Exception that occurred

    Returns:
        Appropriate exit code
    """
    if isinstance(e, AgentflowCLIError):
        output.error(f"Error [{e.code}]: {e.message}", emoji=False)
        for hint in e.hints:
            output.info(f"Try: {hint}", emoji=False)
        if e.docs_url:
            output.info(f"Docs: {e.docs_url}", emoji=False)
        return e.exit_code

    output.error(f"Error [AF-INTERNAL-001]: Unexpected error: {e}", emoji=False)
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
    _configure_command(verbose=verbose, quiet=quiet)

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
    _configure_command(verbose=verbose, quiet=quiet)

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
def dev(
    config: str = typer.Option(
        DEFAULT_CONFIG_FILE,
        "--config",
        "-c",
        help="Path to the project configuration file.",
    ),
    host: str = typer.Option(
        DEFAULT_HOST,
        "--host",
        "-H",
        help="Host interface for the local development server.",
    ),
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port for the local development server.",
    ),
    reload: bool = typer.Option(
        True,
        "--reload/--no-reload",
        help="Reload the server when project files change.",
    ),
    open_playground: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open the hosted playground when the API is ready.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors.",
    ),
) -> None:
    """Start the local Agentflow development server."""
    _configure_command(verbose=verbose, quiet=quiet)

    try:
        command = APICommand(output)
        exit_code = command.execute(
            config=config,
            host=host,
            port=port,
            reload=reload,
            open_playground=open_playground,
        )
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command()
def doctor(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors.",
    ),
) -> None:
    """Diagnose package compatibility and the current project environment."""
    _configure_command(verbose=verbose, quiet=quiet)
    try:
        sys.exit(DoctorCommand(output).execute())
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
    _configure_command(verbose=verbose, quiet=quiet)

    try:
        command = VersionCommand(output)
        exit_code = command.execute()
        sys.exit(exit_code)
    except Exception as e:
        sys.exit(handle_exception(e))


@app.command()
def init(  # noqa: PLR0913
    ctx: typer.Context,
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
    name: str | None = typer.Option(
        None,
        "--name",
        help="Agent name; required only when a default cannot be inferred.",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Project template: quick-start or production.",
    ),
    auth: str | None = typer.Option(
        None,
        "--auth",
        help="Production authentication: none, jwt, or custom.",
    ),
    rate_limit: str | None = typer.Option(
        None,
        "--rate-limit",
        help="Rate limiting: none, memory, or redis.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Accept recommended defaults and do not prompt.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail instead of prompting; suitable for CI and coding agents.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview the scaffold without writing files.",
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
    _configure_command(verbose=verbose, quiet=quiet)
    runtime = ctx.find_root().obj
    if isinstance(runtime, CLIContext):
        yes = yes or runtime.yes
        non_interactive = non_interactive or runtime.non_interactive

    try:
        command = InitCommand(output)
        exit_code = command.execute(
            path=path,
            force=force,
            agent_name=name,
            template=template,
            auth=auth,
            rate_limit=rate_limit,
            yes=yes,
            non_interactive=non_interactive,
            dry_run=dry_run,
        )
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
    k8s: bool = typer.Option(
        False,
        "--k8s/--no-k8s",
        help=(
            "Also generate k8s.yaml (Deployment + Service) with a termination grace "
            "period long enough that a rolling deploy does not kill in-flight agent runs"
        ),
    ),
    service_name: str = typer.Option(
        "agentflow-cli",
        "--service-name",
        help="Service name to use in docker-compose.yml / k8s.yaml (if generated)",
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
    _configure_command(verbose=verbose, quiet=quiet)

    try:
        command = BuildCommand(output)
        exit_code = command.execute(
            output_file=output_file,
            force=force,
            python_version=python_version,
            port=port,
            docker_compose=docker_compose,
            k8s=k8s,
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
    _configure_command(verbose=verbose, quiet=quiet)

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
    _configure_command(verbose=verbose, quiet=quiet)

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
    _configure_command(verbose=verbose, quiet=quiet)

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
