# CLI Commands

Use this when changing `10xscale-agentflow-cli` command behavior, generated files, or deployment scaffolding.

## Package

Install:

```bash
pip install 10xscale-agentflow-cli
```

Entry point:

```text
agentflow = agentflow_cli.cli.main:main
```

## Commands

`agentflow init`

- Scaffolds `agentflow.json`, `graph/__init__.py`, `graph/react.py`, and `skills/agent-skills`.
- Options include `--path/-p`, `--force/-f`, `--prod`, `--verbose/-v`, and `--quiet/-q`.
- `--prod` also adds production project files such as `pyproject.toml` and `.pre-commit-config.yaml`.

`agentflow api`

- Starts the FastAPI server for a compiled graph.
- Options include `--config/-c`, `--host/-H`, `--port/-p`, `--reload/--no-reload`, `--verbose/-v`, and `--quiet/-q`.
- Defaults are config `agentflow.json`, host `0.0.0.0`, port `8000`, reload enabled.

`agentflow play`

- Starts the API server and opens/prints the hosted playground URL.
- Accepts the same server options as `api`.
- Uses host/port to build the playground backend URL.

`agentflow build`

- Generates Docker deployment files.
- Options include `--output/-o`, `--force/-f`, `--python-version`, `--port/-p`, `--docker-compose/--no-docker-compose`, `--service-name`, `--verbose/-v`, and `--quiet/-q`.

`agentflow skills`

- Installs the bundled Agentflow skill into an agent-specific project directory.
- Prompts for the target agent when `--agent` is omitted:
  - `1` / `codex`: `.agent/skills/agentflow`
  - `2` / `claude`: `.claude/skills/agentflow`
  - `3` / `github`: `.github/skills/agentflow`
- Options include `--agent/-a`, `--path/-p`, `--force/-f`, `--verbose/-v`, and `--quiet/-q`.
- Source template: `agentflow-api/agentflow_cli/cli/templates/skills/agent-skills`.

`agentflow version`

- Prints CLI and library version information.

## Rules

- Use docs package names in user-facing text.
- Keep command options aligned with `agentflow-docs/docs/reference/api-cli/commands.md`.
- If command defaults change, update docs, templates, and tests together.
- Generated skill templates live under `agentflow-api/agentflow_cli/cli/templates/skills`.

## Source Map

- CLI main: `agentflow-api/agentflow_cli/cli/main.py`
- Commands: `agentflow-api/agentflow_cli/cli/commands`
- CLI config/output/validation: `agentflow-api/agentflow_cli/cli/core`
- Templates: `agentflow-api/agentflow_cli/cli/templates`
- Main docs: `agentflow-docs/docs/reference/api-cli/commands.md`
- How-to init: `agentflow-docs/docs/how-to/api-cli/initialize-project.md`
- How-to server: `agentflow-docs/docs/how-to/api-cli/run-api-server.md`
