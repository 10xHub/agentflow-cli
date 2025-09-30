# Pyagenity CLI Reference

`pag` is the command-line interface for scaffolding, running, and packaging Pyagenity-based agent APIs.

## Commands

| Command | Description |
|---------|-------------|
| `pag init` | Create `pyagenity.json` and sample graph under `graph/` |
| `pag init --prod` | Same as init plus tooling files (`pyproject.toml`, `.pre-commit-config.yaml`) |
| `pag api` | Run development API server (FastAPI + Uvicorn) |
| `pag build` | Generate Dockerfile (and optional docker-compose.yml) |
| `pag version` | Show CLI and installed package versions |

Run `pag <command> --help` for option details.

## Init
Scaffolds a runnable agent graph.

### Default Files
* `pyagenity.json` – main configuration
* `graph/react.py` – example agent graph (tool, routing, LiteLLM call)
* `graph/__init__.py`

### With `--prod`
Adds:
* `.pre-commit-config.yaml`
* `pyproject.toml`

Flags:
| Flag | Meaning |
|------|---------|
| `--path/-p` | Target directory (default `.`) |
| `--force/-f` | Overwrite existing files |
| `--prod` | Include production tooling |

Example:
```
pag init --prod --path myservice
cd myservice
pre-commit install
```

## API
Starts a development server (hot reload by default).

Key options:
| Option | Default | Notes |
|--------|---------|-------|
| `--config/-c` | `pyagenity.json` | Config file path |
| `--host/-H` | `0.0.0.0` | Use `127.0.0.1` for local only |
| `--port/-p` | `8000` | Port to bind |
| `--reload/--no-reload` | reload on | Auto-reload for dev |

Behavior:
* Loads `.env` (or file specified in config).
* Sets `GRAPH_PATH` env var for runtime.

## Build
Generates production Docker artifacts.

Options:
| Option | Default | Description |
|--------|---------|-------------|
| `--output/-o` | `Dockerfile` | Dockerfile path |
| `--python-version` | `3.13` | Base image tag |
| `--port/-p` | `8000` | Exposed container port |
| `--docker-compose` | off | Also create `docker-compose.yml` and omit CMD |
| `--service-name` | `pyagenity-api` | Compose service name |

Features:
* Auto-detects requirements file (fallback installs `pyagenity-api`).
* Adds health check to `/ping`.
* Uses `gunicorn` + uvicorn worker (production pattern).

## Version
Displays both the CLI internal version and the package version read from `pyproject.toml`.

## Environment Variables Used
| Variable | Purpose |
|----------|---------|
| `GRAPH_PATH` | Path to active config file for graph loading |
| `PYTHONDONTWRITEBYTECODE` | Disable `.pyc` (Docker) |
| `PYTHONUNBUFFERED` | Unbuffered I/O (Docker) |

## Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic failure |
| 2 | Configuration error |
| 3 | Validation error |

## Quick Reference
```
pag init
pag init --prod
pag api --reload
pag build --docker-compose
pag version
```

## Suggestions After `--prod`
1. Edit metadata in `pyproject.toml`.
2. Install hooks: `pre-commit install`.
3. Run tests: `pytest`.
4. Build image: `pag build`.
5. Deploy container.

---
End of CLI reference.
