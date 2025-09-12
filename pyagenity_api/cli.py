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

    uvicorn.run("pyagenity_api.src.app.main:app", host=host, port=port, reload=reload, workers=1)


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


@app.command()
def build(
    output: str = typer.Option("Dockerfile", help="Output Dockerfile path"),
    force: bool = typer.Option(False, help="Overwrite existing Dockerfile"),
    python_version: str = typer.Option("3.11", help="Python version to use"),
    port: int = typer.Option(8000, help="Port to expose in the container"),
):
    """Generate a Dockerfile for the Pyagenity API application."""
    output_path = Path(output)
    current_dir = Path.cwd()

    # Check if Dockerfile already exists
    if output_path.exists() and not force:
        typer.echo(f"Dockerfile already exists at {output_path}", err=True)
        typer.echo("Use --force to overwrite", err=True)
        raise typer.Exit(1)

    # Check for requirements.txt
    requirements_files = []
    requirements_paths = [
        current_dir / "requirements.txt",
        current_dir / "requirements" / "requirements.txt",
        current_dir / "requirements" / "base.txt",
        current_dir / "requirements" / "production.txt",
    ]

    for req_path in requirements_paths:
        if req_path.exists():
            requirements_files.append(req_path)

    if not requirements_files:
        typer.echo("⚠️  Warning: No requirements.txt file found!", err=True)
        typer.echo("Searched in the following locations:", err=True)
        for req_path in requirements_paths:
            typer.echo(f"  - {req_path}", err=True)
        typer.echo("")
        typer.echo("Consider creating a requirements.txt file with your dependencies.", err=True)

        # Ask user if they want to continue
        if not typer.confirm("Continue generating Dockerfile without requirements.txt?"):
            raise typer.Exit(0)

    # Determine the requirements file to use
    requirements_file = "requirements.txt"
    if requirements_files:
        requirements_file = requirements_files[0].name
        if len(requirements_files) > 1:
            typer.echo(f"Found multiple requirements files, using: {requirements_file}")

    # Generate Dockerfile content
    dockerfile_content = generate_dockerfile_content(
        python_version=python_version,
        port=port,
        requirements_file=requirements_file,
        has_requirements=bool(requirements_files),
    )

    # Write Dockerfile
    try:
        with output_path.open("w") as f:
            f.write(dockerfile_content)

        typer.echo(f"✅ Successfully generated Dockerfile at {output_path}")

        if requirements_files:
            typer.echo(f"📦 Using requirements file: {requirements_files[0]}")

        typer.echo("\n🚀 Next steps:")
        typer.echo("1. Review the generated Dockerfile")
        typer.echo("2. Build the Docker image: docker build -t pyagenity-api .")
        typer.echo("3. Run the container: docker run -p 8000:8000 pyagenity-api")

    except Exception as e:
        typer.echo(f"Error writing Dockerfile: {e}", err=True)
        raise typer.Exit(1)


def generate_dockerfile_content(
    python_version: str, port: int, requirements_file: str, has_requirements: bool
) -> str:
    """Generate the content for the Dockerfile."""
    dockerfile_lines = [
        "# Dockerfile for Pyagenity API",
        "# Generated by pyagenity-api CLI",
        "",
        f"FROM python:{python_version}-slim",
        "",
        "# Set environment variables",
        "ENV PYTHONDONTWRITEBYTECODE=1",
        "ENV PYTHONUNBUFFERED=1",
        "ENV PYTHONPATH=/app",
        "",
        "# Set work directory",
        "WORKDIR /app",
        "",
        "# Install system dependencies",
        "RUN apt-get update \\",
        "    && apt-get install -y --no-install-recommends \\",
        "        build-essential \\",
        "        curl \\",
        "    && rm -rf /var/lib/apt/lists/*",
        "",
    ]

    if has_requirements:
        dockerfile_lines.extend(
            [
                "# Install Python dependencies",
                f"COPY {requirements_file} .",
                f"RUN pip install --no-cache-dir --upgrade pip \\",
                f"    && pip install --no-cache-dir -r {requirements_file}",
                "",
            ]
        )
    else:
        dockerfile_lines.extend(
            [
                "# Install pyagenity-api (since no requirements.txt found)",
                "RUN pip install --no-cache-dir --upgrade pip \\",
                "    && pip install --no-cache-dir pyagenity-api",
                "",
            ]
        )

    dockerfile_lines.extend(
        [
            "# Copy application code",
            "COPY . .",
            "",
            "# Create a non-root user",
            "RUN groupadd -r appuser && useradd -r -g appuser appuser \\",
            "    && chown -R appuser:appuser /app",
            "USER appuser",
            "",
            "# Expose port",
            f"EXPOSE {port}",
            "",
            "# Health check",
            f"HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\",
            f"    CMD curl -f http://localhost:{port}/ping || exit 1",
            "",
            "# Run the application",
            f'CMD ["pag", "api", "--host", "0.0.0.0", "--port", "{port}"]',
            "",
        ]
    )

    return "\n".join(dockerfile_lines)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
