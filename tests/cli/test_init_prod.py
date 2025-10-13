"""Tests for `pag init --prod` command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # Invoke the CLI via module to ensure we use this environment's interpreter
    return subprocess.run(
        [sys.executable, "-m", "agentflow_cli.cli.main", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )


def test_init_prod_creates_extra_files(tmp_path: Path) -> None:
    """Ensure prod init creates agentflowjson, graph files, and prod configs."""
    result = run_cli(["init", "--prod"], tmp_path)

    assert result.returncode == 0, result.stderr or result.stdout

    # Core files
    assert (tmp_path / "agentflowjson").exists()
    assert (tmp_path / "graph" / "react.py").exists()
    assert (tmp_path / "graph" / "__init__.py").exists()

    # Production files
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert (tmp_path / "pyproject.toml").exists()

    # Basic sanity check on pyproject content
    content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project]" in content
    assert "agentflow-cli" in content  # dependency reference
