import json
import os
from pathlib import Path

from dotenv import load_dotenv


class GraphConfig:
    def __init__(self, path: str = "agentflow.json"):
        with Path(path).open() as f:
            self.data: dict = json.load(f)

        # load .env file
        env_file = self.data.get("env")
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)

    @property
    def graph_path(self) -> str:
        graphs = self.data.get("graphs", {})
        if "agent" in graphs:
            return graphs["agent"]

        raise ValueError("Agent graph not found")

    @property
    def checkpointer_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "checkpointer" in graphs:
            return graphs["checkpointer"]
        return None

    @property
    def injectq_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "injectq" in graphs:
            return graphs["injectq"]
        return None

    @property
    def store_path(self) -> str | None:
        graphs = self.data.get("graphs", {})
        if "store" in graphs:
            return graphs["store"]
        return None

    @property
    def redis_url(self) -> str | None:
        return self.data.get("redis", None)

    def auth_config(self) -> dict | None:
        res = self.data.get("auth", None)
        if not res:
            return None

        if isinstance(res, str) and "jwt" in res:
            # Now check jwt secret and algorithm available in env
            secret = os.environ.get("JWT_SECRET_KEY", None)
            algorithm = os.environ.get("JWT_ALGORITHM", None)
            if not secret or not algorithm:
                raise ValueError(
                    "JWT_SECRET_KEY and JWT_ALGORITHM must be set in environment variables",
                )
            return {
                "method": "jwt",
            }

        if isinstance(res, dict):
            method = res.get("method", None)
            path: str | None = res.get("path", None)
            if not path or not method:
                raise ValueError("Both method and path must be provided in auth config")

            if method == "custom" and path and Path(path).exists():
                return {
                    "method": "custom",
                    "path": path,
                }

        raise ValueError(f"Unsupported auth method: {res}")

    @property
    def generate_thread_name(self) -> bool:
        return self.data.get("generate_thread_name", False)

    @property
    def thread_model_name(self) -> str | None:
        return self.data.get("thread_model_name", None)
