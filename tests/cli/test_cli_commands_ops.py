import os

import pytest

from agentflow_cli.cli.commands.api import APICommand
from agentflow_cli.cli.commands.build import BuildCommand
from agentflow_cli.cli.commands.init import InitCommand
from agentflow_cli.cli.core.output import OutputFormatter

TEST_PORT = 1234


class SilentOutput(OutputFormatter):  # minimize noise
    def print_banner(self, *args, **kwargs):  # type: ignore[override]
        pass

    def success(self, *args, **kwargs):  # type: ignore[override]
        pass

    def info(self, *args, **kwargs):  # type: ignore[override]
        pass

    def warning(self, *args, **kwargs):  # type: ignore[override]
        pass

    def error(self, *args, **kwargs):  # type: ignore[override]
        pass


@pytest.fixture()
def silent_output():
    return SilentOutput()


def test_api_command_minimal_success(monkeypatch, tmp_path, silent_output):
    monkeypatch.setenv("GRAPH_PATH", "")

    def fake_validate(host, port, config):
        return {"host": host, "port": port, "config": config}

    class FakeConfigManager:
        def find_config_file(self, cfg):
            p = tmp_path / cfg
            p.write_text("{}", encoding="utf-8")
            return p

        def load_config(self, path):  # noqa: D401 - simple stub
            return {}

        def resolve_env_file(self):
            return None

    monkeypatch.setitem(os.environ, "PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr("agentflow_cli.cli.commands.api.validate_cli_options", fake_validate)
    monkeypatch.setattr("agentflow_cli.cli.commands.api.ConfigManager", lambda: FakeConfigManager())

    called = {}

    def fake_run(app_path, host, port, reload, workers):
        called.update(
            {
                "app_path": app_path,
                "host": host,
                "port": port,
                "reload": reload,
                "workers": workers,
            }
        )

    monkeypatch.setattr("agentflow_cli.cli.commands.api.uvicorn.run", fake_run)

    cmd = APICommand(output=silent_output)
    code = cmd.execute(config="test_config.json", host="127.0.0.1", port=TEST_PORT, reload=False)
    assert code == 0
    assert called["app_path"].endswith(":app")
    assert called["port"] == TEST_PORT
    assert os.environ.get("GRAPH_PATH", "").endswith("test_config.json")


def test_api_command_error_path(monkeypatch, silent_output):
    def bad_validate(host, port, config):
        raise ValueError("bad input")

    monkeypatch.setattr("agentflow_cli.cli.commands.api.validate_cli_options", bad_validate)
    cmd = APICommand(output=silent_output)
    code = cmd.execute(config="missing.json")
    assert code == 1


def test_init_command_basic(tmp_path, silent_output):
    cmd = InitCommand(output=silent_output)
    code = cmd.execute(path=str(tmp_path), force=False, prod=False)
    assert code == 0
    assert (tmp_path / "agentflowjson").exists()
    assert (tmp_path / "graph" / "react.py").exists()
    assert (tmp_path / "graph" / "__init__.py").exists()


def test_init_command_prod(tmp_path, silent_output):
    cmd = InitCommand(output=silent_output)
    code = cmd.execute(path=str(tmp_path), force=False, prod=True)
    assert code == 0
    assert (tmp_path / "agentflowjson").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert (tmp_path / "pyproject.toml").exists()


def test_init_command_existing_without_force(tmp_path, silent_output):
    cfg = tmp_path / "agentflowjson"
    cfg.write_text("{}", encoding="utf-8")
    cmd = InitCommand(output=silent_output)
    code = cmd.execute(path=str(tmp_path), force=False)
    assert code == 1


def test_build_command_basic_no_requirements(tmp_path, monkeypatch, silent_output):
    monkeypatch.chdir(tmp_path)
    cmd = BuildCommand(output=silent_output)
    code = cmd.execute(output_file="Dockerfile", force=True, docker_compose=False)
    assert code == 0
    content = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM" in content
    assert "CMD" in content


def test_build_command_with_compose(tmp_path, monkeypatch, silent_output):
    monkeypatch.chdir(tmp_path)
    cmd = BuildCommand(output=silent_output)
    code = cmd.execute(
        output_file="Dockerfile",
        force=True,
        docker_compose=True,
        service_name="svc",
    )
    assert code == 0
    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM" in dockerfile
    # The dockerfile should include the healthcheck CMD curl line but omit the final
    # application run command (CMD ["gunicorn", ...]) when docker_compose=True (omit_cmd=True).
    # 'gunicorn' will still appear in the installation RUN line, so we specifically
    # assert that no line starts with the application CMD instruction.
    assert 'CMD ["gunicorn"' not in dockerfile
    assert (tmp_path / "docker-compose.yml").exists()


def test_build_command_compose_existing_without_force(tmp_path, monkeypatch, silent_output):
    monkeypatch.chdir(tmp_path)
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("version: '3'", encoding="utf-8")
    cmd = BuildCommand(output=silent_output)
    code = cmd.execute(output_file="Dockerfile", force=False, docker_compose=True)
    assert code == 1


def test_init_command_force_overwrite(tmp_path, silent_output):
    # Create initial files
    cfg = tmp_path / "agentflowjson"
    react_dir = tmp_path / "graph"
    react_dir.mkdir()
    react_file = react_dir / "react.py"
    cfg.write_text("{}", encoding="utf-8")
    react_file.write_text("print('old')", encoding="utf-8")
    # Execute with force=True should succeed (0) and overwrite
    cmd = InitCommand(output=silent_output)
    code = cmd.execute(path=str(tmp_path), force=True, prod=False)
    assert code == 0
    # Confirm file content overwritten (no longer the initial minimal JSON '{}')
    new_content = cfg.read_text(encoding="utf-8")
    assert new_content.strip() != "{}"
    assert '"graphs"' in new_content


def test_build_command_multiple_requirements(tmp_path, monkeypatch, silent_output):
    monkeypatch.chdir(tmp_path)
    # Create multiple requirement files so branch logging about multiple found triggers
    (tmp_path / "requirements.txt").write_text("fastapi==0.1", encoding="utf-8")
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("uvicorn==0.1", encoding="utf-8")
    cmd = BuildCommand(output=silent_output)
    code = cmd.execute(output_file="Dockerfile", force=True, docker_compose=False)
    assert code == 0
    content = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    # Should still include CMD (not docker-compose) and chosen first requirements.txt
    assert 'CMD ["gunicorn"' in content
    assert "requirements.txt" in content


def test_build_command_compose_force_overwrite(tmp_path, monkeypatch, silent_output):
    monkeypatch.chdir(tmp_path)
    compose = tmp_path / "docker-compose.yml"
    compose.write_text("services:\n  old: {}\n", encoding="utf-8")
    cmd = BuildCommand(output=silent_output)
    code = cmd.execute(output_file="Dockerfile", force=True, docker_compose=True)
    assert code == 0
    assert (tmp_path / "docker-compose.yml").read_text(encoding="utf-8").startswith("services:")
