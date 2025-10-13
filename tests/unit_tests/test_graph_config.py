import json
from pathlib import Path

import pytest

from agentflow_cli.src.app.core.config.graph_config import GraphConfig


def test_graph_config_reads_agent(tmp_path: Path):
    cfg_path = tmp_path / "cfg.json"
    data = {
        "graphs": {
            "agent": "mod:func",
            "checkpointer": "ckpt:fn",
            "store": "store.mod:store",
        }
    }
    cfg_path.write_text(json.dumps(data))

    cfg = GraphConfig(str(cfg_path))
    assert cfg.graph_path == "mod:func"
    assert cfg.checkpointer_path == "ckpt:fn"
    assert cfg.store_path == "store.mod:store"


def test_graph_config_missing_agent_raises(tmp_path: Path):
    cfg_path = tmp_path / "cfg.json"
    data = {"graphs": {}}
    cfg_path.write_text(json.dumps(data))

    with pytest.raises(ValueError):
        _ = GraphConfig(str(cfg_path)).graph_path
