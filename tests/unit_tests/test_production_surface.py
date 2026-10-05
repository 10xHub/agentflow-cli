"""Production does not expose dev-only surfaces (M3, M4).

- The evals report viewer has no auth, so it is not mounted in production.
- API docs and the OpenAPI schema are off in production unless a path is set explicitly.
- Generated Docker builds do not copy local uploads or eval reports into the image.
"""

# ruff: noqa: S101

from fastapi import FastAPI

from agentflow_cli.cli.templates.defaults import generate_dockerignore_content
from agentflow_cli.src.app.core.auth.route_guard import _iter_routes
from agentflow_cli.src.app.core.config.settings import Settings
from agentflow_cli.src.app.routers.setup_router import init_routes


def _paths(app: FastAPI) -> set[str]:
    return {path for path, _route, _guarded in _iter_routes(app.routes)}


def test_evals_viewer_is_mounted_by_default():
    app = FastAPI()
    init_routes(app)
    assert "/v1/evals/runs" in _paths(app)


def test_evals_viewer_can_be_left_out():
    app = FastAPI()
    init_routes(app, evals=False)
    assert not any(path.startswith("/v1/evals") for path in _paths(app))


def test_docs_are_off_in_production_by_default(monkeypatch):
    monkeypatch.delenv("DOCS_PATH", raising=False)
    monkeypatch.delenv("REDOCS_PATH", raising=False)
    settings = Settings(MODE="production", _env_file=None)
    assert (settings.DOCS_PATH, settings.REDOCS_PATH) == ("", "")


def test_docs_explicitly_enabled_in_production_stay_on(monkeypatch):
    monkeypatch.delenv("REDOCS_PATH", raising=False)
    settings = Settings(MODE="production", DOCS_PATH="/docs", _env_file=None)
    assert settings.DOCS_PATH == "/docs"


def test_docs_stay_on_in_development(monkeypatch):
    monkeypatch.delenv("DOCS_PATH", raising=False)
    settings = Settings(MODE="development", _env_file=None)
    assert settings.DOCS_PATH == "/docs"


def test_dockerignore_excludes_local_data():
    lines = generate_dockerignore_content().splitlines()
    assert "uploads/" in lines
    assert "eval_reports/" in lines


# ---------------------------------------------------------------------------
# M10: the generated Dockerfile installs the real package and the project's deps
# ---------------------------------------------------------------------------


def _dockerfile(**kwargs) -> str:
    from agentflow_cli.cli.templates.defaults import generate_dockerfile_content

    return generate_dockerfile_content("3.13", 8000, "requirements.txt", **kwargs)


def _pip_packages(dockerfile: str) -> set[str]:
    commands = [line for line in dockerfile.splitlines() if not line.lstrip().startswith("#")]
    words = " ".join(commands).split()
    return {w for w in words if "agentflow" in w and ":" not in w}


def test_dockerfile_installs_the_published_cli_package():
    content = _dockerfile(has_requirements=False)
    assert "10xscale-agentflow-cli" in _pip_packages(content)
    assert "agentflow-cli" not in _pip_packages(content)


def test_dockerfile_installs_pyproject_dependencies():
    content = _dockerfile(has_requirements=False, has_pyproject=True)
    assert "COPY pyproject.toml ." in content
    assert "pip install --no-cache-dir -r /tmp/requirements.txt" in content


def test_requirements_file_still_wins():
    content = _dockerfile(has_requirements=True, has_pyproject=True)
    assert "-r requirements.txt" in content
    assert "pyproject.toml" not in content
