"""Read and atomically write the ``agentflow.json`` file being edited."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigConflictError(Exception):
    """The file changed on disk after the editor loaded it."""


@dataclass(frozen=True)
class LoadedConfig:
    config: dict[str, Any] | None
    version: str | None  # sha256 of the file bytes, None when the file does not exist
    parse_error: str | None = None


class ConfigFileStore:
    """Owns one config file: loads it, detects concurrent edits, and saves it safely."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def backup_path(self) -> Path:
        return self.path.with_name(f"{self.path.name}.bak")

    def load(self) -> LoadedConfig:
        if not self.path.exists():
            return LoadedConfig(config=None, version=None)
        raw = self.path.read_bytes()
        version = _digest(raw)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return LoadedConfig(config=None, version=version, parse_error=str(exc))
        if not isinstance(data, dict):
            return LoadedConfig(
                config=None, version=version, parse_error="The file is not a JSON object."
            )
        return LoadedConfig(config=data, version=version)

    def save(self, config: dict[str, Any], expected_version: str | None) -> str:
        """Write ``config`` and return the new version.

        Raises:
            ConfigConflictError: The file on disk no longer matches ``expected_version``.
        """
        current = self.load()
        if current.version != expected_version:
            raise ConfigConflictError(
                f"{self.path.name} changed on disk after it was loaded. Reload to see the "
                "latest version before saving."
            )

        ordered = _preserve_key_order(config, current.config or {})
        payload = (json.dumps(ordered, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            shutil.copy2(self.path, self.backup_path)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return _digest(payload)


def _preserve_key_order(new: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    """Keep the file's existing top-level key order; append new keys at the end."""
    ordered = {key: new[key] for key in old if key in new}
    ordered.update({key: value for key, value in new.items() if key not in ordered})
    return ordered


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
