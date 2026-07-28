"""Cross-platform user preferences for the Agentflow CLI."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from agentflow_cli.cli.exceptions import ConfigurationError


class UserConfigStore:
    """Read and atomically update non-secret per-user CLI preferences."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_config_path("agentflow", "10xscale") / "config.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": self.SCHEMA_VERSION}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"Could not read user configuration at {self.path}: {exc}",
                config_path=str(self.path),
            ) from exc
        if not isinstance(raw, dict):
            raise ConfigurationError(
                f"User configuration at {self.path} must be a JSON object.",
                config_path=str(self.path),
            )
        return raw

    def get(self, key: str, default: Any = None) -> Any:
        value: Any = self.load()
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def set(self, key: str, value: Any) -> None:
        data = self.load()
        target = data
        parts = key.split(".")
        if not all(parts):
            raise ConfigurationError("Configuration key cannot be empty.")
        for part in parts[:-1]:
            existing = target.get(part)
            if existing is None:
                existing = {}
                target[part] = existing
            if not isinstance(existing, dict):
                raise ConfigurationError(
                    f"Cannot set '{key}': '{part}' already contains a scalar value.",
                    config_path=str(self.path),
                )
            target = existing
        target[parts[-1]] = value
        data["schema_version"] = self.SCHEMA_VERSION
        self._write(data)

    def unset(self, key: str) -> bool:
        data = self.load()
        target: Any = data
        parts = key.split(".")
        for part in parts[:-1]:
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        if not isinstance(target, dict) or parts[-1] not in target:
            return False
        del target[parts[-1]]
        self._write(data)
        return True

    def _write(self, data: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary_path.replace(self.path)
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()
        except OSError as exc:
            raise ConfigurationError(
                f"Could not write user configuration at {self.path}: {exc}",
                config_path=str(self.path),
            ) from exc


def parse_config_value(value: str) -> Any:
    """Parse JSON scalars/containers while retaining ordinary strings."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
