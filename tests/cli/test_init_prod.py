"""Tests for `10xgraph init` production setup."""

from __future__ import annotations

import io
from pathlib import Path

from tenxgraph_api.cli.commands.init import InitCommand
from tenxgraph_api.cli.core.output import OutputFormatter


def SilentOutput() -> OutputFormatter:
    """A real formatter with output suppressed, so it tracks the live surface."""
    return OutputFormatter(stream=io.StringIO(), quiet=True)


def _skip_binary(original):
    """Wrap _should_skip to also exclude non-text template artifacts."""

    def patched(self, src, template_dir, context, is_prod):
        if any(part in {".ruff_cache", "__pycache__"} for part in src.parts):
            return True
        return original(self, src, template_dir, context, is_prod)

    return patched


def test_init_prod_creates_extra_files(monkeypatch, tmp_path: Path) -> None:
    """Ensure prod init creates 10xgraph.json, graph files, and prod configs."""
    ctx = {
        "agent_name": "MyAgent",
        "agent_name_slug": "my-agent",
        "setup_type": "production",
        "auth": "none",
        "rate_limit": "none",
    }
    monkeypatch.setattr(InitCommand, "_prompt_user", lambda self: ctx)
    monkeypatch.setattr(InitCommand, "_should_skip", _skip_binary(InitCommand._should_skip))

    cmd = InitCommand(output=SilentOutput())
    code = cmd.execute(path=str(tmp_path), force=False)

    assert code == 0, "InitCommand.execute() returned non-zero"

    # Core files
    assert (tmp_path / "10xgraph.json").exists()
    assert (tmp_path / "graph" / "agent.py").exists()
    assert (tmp_path / "graph" / "__init__.py").exists()

    # Production files — accept either spelling of the pre-commit config filename
    assert (tmp_path / "pyproject.toml").exists()
    assert any(
        (tmp_path / f).exists() for f in (".pre-commit-config.yaml", ".pre-commot-config.yaml")
    )

    # Basic sanity check on pyproject content
    content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project]" in content
    assert "10xgraph-api" in content


def test_init_prod_skips_binary_template_artifacts() -> None:
    cmd = InitCommand(output=SilentOutput())
    assert cmd._should_skip(
        Path("tenxgraph_api/cli/templates/prod/.ruff_cache/0.5.2/17065574497421059950"),
        Path("tenxgraph_api/cli/templates/prod"),
        {},
        True,
    )
    assert cmd._should_skip(
        Path(
            "tenxgraph_api/cli/templates/prod/tests/__pycache__/test_graph_nodes.cpython-313-pytest-9.0.3.pyc"
        ),
        Path("tenxgraph_api/cli/templates/prod"),
        {},
        True,
    )
