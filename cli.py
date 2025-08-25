import logging
import os

import typer
import uvicorn
from dotenv import load_dotenv


load_dotenv()

# Basic logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = typer.Typer()


@app.command()
def api(
    config: str = typer.Option("pyagenity.json", help="Path to config file"),
    host: str = typer.Option(
        "0.0.0.0",  # noqa: S104
        help="Host to run the API on (default: 0.0.0.0, binds to all interfaces;"
        " use 127.0.0.1 for localhost only)",
    ),
    port: int = typer.Option(8000, help="Port to run the API on"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    logging.info(f"Starting API with config: {config}, host: {host}, port: {port}")
    os.environ["GRAPH_PATH"] = config
    uvicorn.run("src.app.main:app", host=host, port=port, reload=reload, workers=1)


@app.command()
def version():
    """Show the CLI version."""
    typer.echo("pyagenity-api CLI version 1.0.0")


if __name__ == "__main__":
    app()
