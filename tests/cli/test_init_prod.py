"""Tests for `agentflow init` production setup."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentflow_cli.cli.commands.init import InitCommand


class SilentOutput:
    def print_banner(self, *a, **kw):
        pass

    def success(self, *a, **kw):
        pass

    def info(self, *a, **kw):
        pass

    def warning(self, *a, **kw):
        pass

    def error(self, *a, **kw):
        pass


def _skip_binary(original):
    """Wrap _should_skip to also exclude non-text template artifacts."""

    def patched(self, src, template_dir, context, is_prod):
        if any(part in {".ruff_cache", "__pycache__"} for part in src.parts):
            return True
        return original(self, src, template_dir, context, is_prod)

    return patched


def test_init_prod_creates_extra_files(monkeypatch, tmp_path: Path) -> None:
    """Ensure prod init creates agentflow.json, graph files, and prod configs."""
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
    assert (tmp_path / "agentflow.json").exists()
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
    assert "agentflow-cli" in content


def test_init_prod_skips_binary_template_artifacts() -> None:
    cmd = InitCommand(output=SilentOutput())
    assert cmd._should_skip(
        Path("agentflow_cli/cli/templates/prod/.ruff_cache/0.5.2/17065574497421059950"),
        Path("agentflow_cli/cli/templates/prod"),
        {},
        True,
    )
    assert cmd._should_skip(
        Path(
            "agentflow_cli/cli/templates/prod/tests/__pycache__/test_graph_nodes.cpython-313-pytest-9.0.3.pyc"
        ),
        Path("agentflow_cli/cli/templates/prod"),
        {},
        True,
    )
