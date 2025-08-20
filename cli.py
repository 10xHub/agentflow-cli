import os

import typer
import uvicorn
from dotenv import load_dotenv


load_dotenv()

app = typer.Typer()


@app.command()
def api(config: str = "pyagenity.json", host: str = "0.0.0.0", port: int = 8000):
    print(f"Starting API with config: {config}, host: {host}, port: {port}")
    os.environ["GRAPH_PATH"] = config
    uvicorn.run("src.app.main:app", host=host, port=port, reload=False, workers=1)


if __name__ == "__main__":
    app()
