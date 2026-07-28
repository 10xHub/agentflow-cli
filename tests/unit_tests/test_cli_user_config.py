"""User configuration persistence and command tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentflow_cli.cli.exceptions import ConfigurationError
from agentflow_cli.cli.user_config import UserConfigStore, parse_config_value


def test_store_round_trip_and_unset(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = UserConfigStore(path)
    assert store.load() == {"schema_version": 1}

    store.set("output.format", "plain")
    store.set("updates.enabled", False)
    assert store.get("output.format") == "plain"
    assert store.get("updates.enabled") is False
    assert store.get("missing", "fallback") == "fallback"
    assert store.unset("output.format") is True
    assert store.unset("output.format") is False

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 1
    assert persisted["updates"]["enabled"] is False


def test_store_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Could not read"):
        UserConfigStore(path).load()


def test_store_rejects_scalar_parent(tmp_path: Path) -> None:
    store = UserConfigStore(tmp_path / "config.json")
    store.set("output", "plain")
    with pytest.raises(ConfigurationError, match="scalar"):
        store.set("output.format", "json")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("42", 42),
        ('{"a": 1}', {"a": 1}),
        ("plain", "plain"),
    ],
)
def test_parse_config_value(raw, expected) -> None:
    assert parse_config_value(raw) == expected
