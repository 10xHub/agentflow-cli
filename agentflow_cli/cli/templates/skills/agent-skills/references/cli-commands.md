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
- Defaults are config `agentflow.json`, host `127.0.0.1`, port `8000`, reload enabled.

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
  - `1` / `codex`: `.agents/skills/agentflow`
  - `2` / `claude`: `.claude/skills/agentflow`
  - `3` / `github`: `.github/instructions/agentflow.instructions.md` and `.github/skills/agentflow`
- Options include `--agent/-a`, `--path/-p`, `--force/-f`, `--verbose/-v`, and `--quiet/-q`.
- Source templates: https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/cli/templates/skills

`agentflow version`

- Prints CLI and library version information.

## Rules

- Use docs package names in user-facing text.
- Keep command options aligned with https://agentflow.10xscale.ai/
- If command defaults change, update docs, templates, and tests together.
- Generated skill templates live under https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/cli/templates/skills

## Source Map

- CLI main: https://github.com/10xHub/agentflow-cli/blob/main/agentflow_cli/cli/main.py
- Commands: https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/cli/commands
- CLI config/output/validation: https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/cli/core
- Templates: https://github.com/10xHub/agentflow-cli/tree/main/agentflow_cli/cli/templates
- Docs: https://agentflow.10xscale.ai/
