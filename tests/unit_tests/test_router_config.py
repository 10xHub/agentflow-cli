"""Unit tests for the ``routers`` block of agentflow.json.

The block is permissive on purpose: a bad entry never fails the boot, it warns and is
ignored. These tests pin both halves of that -- what a valid entry does, and that an invalid
one leaves the router mounted while saying so in the log.
"""

import json
import logging
from pathlib import Path

from agentflow_cli.src.app.core.config.graph_config import (
    ALWAYS_ON_ROUTERS,
    TOGGLEABLE_ROUTERS,
    GraphConfig,
    RouterConfig,
)


LOGGER_NAME = "agentflow_api"


class TestRouterConfig:
    def test_absent_block_enables_every_router(self):
        config = RouterConfig.from_dict({})

        for name in (*TOGGLEABLE_ROUTERS, *ALWAYS_ON_ROUTERS):
            assert config.is_enabled(name) is True

    def test_false_disables_that_router_only(self):
        config = RouterConfig.from_dict({"evals": False})

        assert config.is_enabled("evals") is False
        assert config.is_enabled("media") is True
        assert config.is_enabled("store") is True
        assert config.is_enabled("checkpointer") is True

    def test_true_keeps_router_enabled(self):
        assert RouterConfig.from_dict({"evals": True}).is_enabled("evals") is True

    def test_string_boolean_is_accepted(self):
        # The rest of agentflow.json accepts "false" as well as false.
        assert RouterConfig.from_dict({"media": "false"}).is_enabled("media") is False

    def test_unknown_router_warns_and_disables_nothing(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            config = RouterConfig.from_dict({"eval": False})

        assert config.disabled == frozenset()
        assert "eval" in caplog.text

    def test_always_on_router_warns_and_stays_mounted(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            config = RouterConfig.from_dict({"graph": False, "ping": False})

        assert config.is_enabled("graph") is True
        assert config.is_enabled("ping") is True
        assert "graph" in caplog.text
        assert "ping" in caplog.text

    def test_non_boolean_value_warns_and_is_ignored(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            config = RouterConfig.from_dict({"evals": "maybe"})

        assert config.is_enabled("evals") is True
        assert "evals" in caplog.text

    def test_non_object_block_warns_and_enables_everything(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            config = RouterConfig.from_dict(["evals"])

        assert config.disabled == frozenset()
        assert caplog.text != ""


class TestGraphConfigRouters:
    def test_absent_key_enables_everything(self, tmp_path: Path):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps({"agent": "mod:func"}))

        assert GraphConfig(str(cfg_path)).routers.disabled == frozenset()

    def test_reads_disabled_routers(self, tmp_path: Path):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(
            json.dumps({"agent": "mod:func", "routers": {"evals": False, "media": False}})
        )

        routers = GraphConfig(str(cfg_path)).routers
        assert routers.disabled == frozenset({"evals", "media"})
        assert routers.is_enabled("store") is True


class TestWebSocketRouterName:
    """``websocket`` is spellable in the routers block as well as its own."""

    def test_websocket_is_toggleable(self):
        assert "websocket" in TOGGLEABLE_ROUTERS

    def test_false_disables_websocket(self):
        assert RouterConfig.from_dict({"websocket": False}).is_enabled("websocket") is False

    def test_absent_leaves_websocket_enabled(self):
        assert RouterConfig.from_dict({"evals": False}).is_enabled("websocket") is True
