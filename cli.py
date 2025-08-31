import json
import logging
import os
import sys
from pathlib import Path


try:
    import importlib.resources

    HAS_IMPORTLIB_RESOURCES = True
except ImportError:
    importlib = None  # type: ignore
    HAS_IMPORTLIB_RESOURCES = False

import typer
import uvicorn
from dotenv import load_dotenv


load_dotenv()

# Basic logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = typer.Typer()


def find_config_file(config_path: str) -> str:
    """
    Find the config file in the following order:
    1. Absolute path if provided
    2. Relative to current working directory
    3. In the package installation directory (fallback)
    """
    config_path_obj = Path(config_path)

    # If absolute path is provided, use it directly
    if config_path_obj.is_absolute():
        if not config_path_obj.exists():
            typer.echo(f"Error: Config file not found at {config_path}", err=True)
            raise typer.Exit(1)
        return str(config_path_obj)

    # Check if file exists in current working directory
    cwd_config = Path.cwd() / config_path
    if cwd_config.exists():
        return str(cwd_config)

    # Check if file exists relative to the script location (for development)
    script_dir = Path(__file__).parent
    script_config = script_dir / config_path
    if script_config.exists():
        return str(script_config)

    # Try to find in package data (when installed)
    if HAS_IMPORTLIB_RESOURCES and importlib:
        try:
            # Try to find the config in the package
            files = importlib.resources.files("pyagenity_api")
            if files:
                package_config = files / config_path
                # Check if the file exists by trying to read it
                try:
                    package_config.read_text()
                    return str(package_config)
                except (FileNotFoundError, OSError):
                    pass
        except (ImportError, AttributeError):
            pass

    # If still not found, suggest creating one
    typer.echo(f"Error: Config file '{config_path}' not found in:", err=True)
    typer.echo(f"  - {cwd_config}", err=True)
    typer.echo(f"  - {script_config}", err=True)
    typer.echo("", err=True)
    typer.echo("Please ensure the config file exists or provide an absolute path.", err=True)
    raise typer.Exit(1)


@app.command()
def api(
    config: str = typer.Option("pyagenity.json", help="Path to config file"),
    host: str = typer.Option(
        "0.0.0.0",  # noqa: S104  # Binding to all interfaces for server
        help="Host to run the API on (default: 0.0.0.0, binds to all interfaces;"
        " use 127.0.0.1 for localhost only)",
    ),
    port: int = typer.Option(8000, help="Port to run the API on"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    """Start the Pyagenity API server."""
    # Find the actual config file path
    actual_config_path = find_config_file(config)

    logging.info(f"Starting API with config: {actual_config_path}, host: {host}, port: {port}")
    os.environ["GRAPH_PATH"] = actual_config_path

    # Ensure we're using the correct module path
    sys.path.insert(0, str(Path(__file__).parent))

    uvicorn.run("src.app.main:app", host=host, port=port, reload=reload, workers=1)


@app.command()
def version():
    """Show the CLI version."""
    typer.echo("pyagenity-api CLI version 1.0.0")


@app.command()
def init(
    output: str = typer.Option("pyagenity.json", help="Output config file path"),
    force: bool = typer.Option(False, help="Overwrite existing config file"),
):
    """Initialize a new config file with default settings."""
    output_path = Path(output)

    if output_path.exists() and not force:
        typer.echo(f"Config file already exists at {output_path}", err=True)
        typer.echo("Use --force to overwrite", err=True)
        raise typer.Exit(1)

    # Create default config
    default_config = {
        "app": {"name": "Pyagenity API", "version": "1.0.0", "debug": True},
        "server": {
            "host": "0.0.0.0",  # noqa: S104  # Default server binding
            "port": 8000,
            "workers": 1,
        },
        "database": {"url": "sqlite://./pyagenity.db"},
        "redis": {"url": "redis://localhost:6379"},
    }

    with output_path.open("w") as f:
        json.dump(default_config, f, indent=2)

    typer.echo(f"Created config file at {output_path}")
    typer.echo("You can now run: pyagenity api")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
