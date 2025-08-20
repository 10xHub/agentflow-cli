import json
from pathlib import Path

from dotenv import load_dotenv


class GraphConfig:
    def __init__(self, path: str):
        with Path(path).open() as f:
            self.data: dict = json.load(f)

        # load .env file
        env_file = self.data.get("env")
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)

    @property
    def graph_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "agent" in graphs:
            return graphs["agent"]
        return None

    @property
    def checkpointer_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "checkpointer" in graphs:
            return graphs["checkpointer"]
        return None

    @property
    def store_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "store" in graphs:
            return graphs["store"]
        return None
