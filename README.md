
# 10xGraph API

> Formerly `10xscale-agentflow-cli`. Upgrading? See
> [Migrating from 10xscale-agentflow-cli](#migrating-from-10xscale-agentflow-cli).

[![CI](https://github.com/10xGraph/10xgraph-api/actions/workflows/ci.yaml/badge.svg)](https://github.com/10xGraph/10xgraph-api/actions/workflows/ci.yaml)
[![Release](https://github.com/10xGraph/10xgraph-api/actions/workflows/release.yml/badge.svg)](https://github.com/10xGraph/10xgraph-api/actions/workflows/release.yml)

[![PyPI](https://img.shields.io/pypi/v/10xgraph-api?color=blue)](https://pypi.org/project/10xgraph-api/)
[![Python](https://img.shields.io/pypi/pyversions/10xgraph-api)](https://pypi.org/project/10xgraph-api/)
[![License](https://img.shields.io/github/license/10xGraph/10xgraph-api)](https://github.com/10xGraph/10xgraph-api/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/10xGraph/10xgraph-api/actions/workflows/ci.yaml)
[![Tests](https://img.shields.io/badge/tests-871%20passed-brightgreen.svg)](https://github.com/10xGraph/10xgraph-api/actions/workflows/ci.yaml)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://pypi.org/project/10xgraph-api/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**10xGraph API** turns a 10xGraph `CompiledGraph` into a production-grade FastAPI service, plus a Typer-based command line to scaffold, run, build, test, and evaluate it. You write a graph, point `10xgraph.json` at it, and `10xgraph api` serves it over REST + WebSocket with authentication, rate limiting, media handling, checkpointer/thread management, and a memory store API.

> ### 📦 Part of the 10xGraph library
>
> This package (`10xgraph-api`) is the **API server + CLI layer** of
> [**10xGraph**](https://github.com/10xGraph/10xGraph). The core orchestration
> engine (`StateGraph`, `Agent`, `ToolNode`, state, persistence, memory, and tools) lives in the
> separate [`10xgraph`](https://pypi.org/project/10xgraph/) package. This package
> builds on top of it to expose your agent graphs as a deployable service.
>
> - **Core framework:** [`10xgraph`](https://pypi.org/project/10xgraph/) · [source](https://github.com/10xGraph/10xGraph)
> - **This package (API + CLI):** [`10xgraph-api`](https://pypi.org/project/10xgraph-api/) · [source](https://github.com/10xGraph/10xgraph-api)
> - **TypeScript client:** [`@10xscale/agentflow-client`](https://www.npmjs.com/package/@10xscale/agentflow-client)
> - **Docs:** [10xgraph.com](https://10xgraph.com/)

---

## Migrating from 10xscale-agentflow-cli

10xGraph is the new name of 10xScale Agentflow. The server, CLI, license and maintainers are
the same, and existing projects keep working.

| | Before | Now |
|---|---|---|
| PyPI package | `10xscale-agentflow-cli` | `10xgraph-api` |
| Python import | `agentflow_cli` | `tenxgraph_api` |
| Command | `agentflow` | `10xgraph` |
| Config file | `agentflow.json` | `10xgraph.json` |
| Core framework | `10xscale-agentflow` (import `agentflow`) | `10xgraph` (import `tenxgraph`) |
| CLI env vars | `AGENTFLOW_NO_FULLSCREEN`, `AGENTFLOW_NO_SPINNER`, `AGENTFLOW_ASCII` | `TENXGRAPH_NO_FULLSCREEN`, `TENXGRAPH_NO_SPINNER`, `TENXGRAPH_ASCII` |
| Website | agentflow.10xscale.ai | [10xgraph.com](https://10xgraph.com) |
| GitHub | [github.com/10xHub](https://github.com/10xHub) | [github.com/10xGraph](https://github.com/10xGraph) |

```bash
pip uninstall 10xscale-agentflow-cli 10xscale-agentflow
pip install 10xgraph-api
```

The old core and the new one both ship an `agentflow` module, so do not install
`10xscale-agentflow` next to `10xgraph`.

Kept working until 2.0, so you can migrate at your own pace:

- **`agentflow` command.** Runs the same CLI and prints a one-line deprecation notice.
- **`from agentflow_cli import ...`.** Resolves to the same modules as `tenxgraph_api` and
  emits a `DeprecationWarning`.
- **`agentflow.json`.** Read when no `10xgraph.json` sits in the same directory. When both
  exist, `10xgraph.json` wins. Rename the file when convenient: the keys are unchanged.
- **`AGENTFLOW_*` CLI env vars.** Read when the `TENXGRAPH_*` variable is unset.
- **`agentflow-bearer` WebSocket subprotocol and `agentflow://media/` URLs.** Still accepted.
  New media references are written as `graph://media/`, and the server now also accepts
  `10xgraph-bearer`.

---

## ✨ Key Features

- **🖥️ Professional CLI** - Scaffold, run, build, test, and evaluate agents from one command line
- **⚡ FastAPI Backend** - Your compiled graph auto-served over REST + WebSocket, high-performance and async
- **🔌 Config-Driven** - One `10xgraph.json` wires agent, auth, checkpointer, store, Redis, and rate limits
- **🔐 Authentication** - Built-in JWT auth, custom `BaseAuth` backends, and RBAC authorization
- **🚦 Rate Limiting** - Sliding-window limits with memory, Redis, or custom backends
- **🆔 Distributed IDs** - Snowflake ID generation for multi-node deployments
- **🧵 Thread Management** - Conversation thread naming, listing, state, and message APIs
- **🖼️ Multimodal & Media** - File upload/download endpoints and media handling for multimodal agents
- **🎙️ Realtime Audio Bridge** - WebSocket endpoint for live audio-to-audio agents (Gemini Live)
- **🐳 Docker & Kubernetes Ready** - Generate production Dockerfiles and compose files with one command
- **🛡️ Production Hardening** - Error/log sanitization, request size limits, security headers, startup validation
- **💉 Dependency Injection** - InjectQ for clean, testable dependency wiring

---

## Installation

**Basic installation:**

```bash
pip install 10xgraph-api
```

Optional extras — install only what you configure:

```bash
pip install "10xgraph-api[redis]"   # Redis rate-limit / cache backend
pip install "10xgraph-api[jwt]"     # JWT authentication
pip install "10xgraph-api[media]"   # Document text extraction (multimodal)
pip install "10xgraph-api[otel]"    # OpenTelemetry tracing
pip install "10xgraph-api[snowflakekit]"  # Snowflake ID generation
```

Requires **Python ≥ 3.12**. Depends on the core `10xgraph` framework.

---

## 🚀 Quick Start

```bash
# 1. Scaffold a project (interactive: dev vs production, auth, rate limiting)
10xgraph init

# 2. Start the local development server and open the playground (127.0.0.1:8000)
10xgraph dev

# 3. Check the environment if anything looks wrong
10xgraph audit

# 4. Generate production Docker files
10xgraph build --docker-compose
```

`10xgraph api` (server only) and `10xgraph play` (server + playground) remain
available; `dev` is the goal-oriented wrapper around them.

---

## 🖥️ CLI Commands

Run `10xgraph --help` or `10xgraph COMMAND --help` for the generated command reference.

### `10xgraph init`

Initialize a new project with configuration and a sample graph.

```bash
10xgraph init                  # interactive (chooses dev vs production setup)
10xgraph init --path ./my-app  # custom directory
10xgraph init --force          # overwrite existing files
10xgraph init --path ./my-app --name MyAgent --template quick-start \
  --non-interactive            # reproducible CI/agent workflow
10xgraph init --path ./my-app --template production --auth jwt \
  --rate-limit redis --yes --dry-run
```

### `10xgraph dev`

Start the development API server and open the hosted playground when it is ready.

```bash
10xgraph dev                              # defaults (127.0.0.1:8000)
10xgraph dev --host 127.0.0.1 --port 9000 # custom host/port
10xgraph dev --config production.json     # custom config file
10xgraph dev --no-open --no-reload        # API only, without auto-reload
```

`10xgraph api` and `10xgraph play` remain available as compatibility commands.

### Adaptive and structured output

```bash
10xgraph play                         # full-screen surface in an interactive terminal
10xgraph demo                         # preview every animation theme safely
10xgraph demo --style build           # one theme: typing, network, init, build, or eval
10xgraph --no-fullscreen play         # keep output in your normal scrollback
10xgraph --no-animation play          # accessible/static workflow
10xgraph --format plain --no-color audit
10xgraph --format jsonl eval --parallel
10xgraph --quiet build
10xgraph --cwd ../my-agent dev
```

On an interactive terminal a command runs on its own full-screen surface: a
pinned header (identity, version, subtitle), a pinned footer status bar, and the
command's output scrolling between them. The intro reveals the 10xGraph
wordmark on the full canvas and collapses into that header, and each command
shows its own pipeline — `play`/`dev` config→runtime→server→playground, `init`
template→graph→config→project, `build` source→deps→image→ship, `eval`
discover→load→score→report, `audit` python→core→config→port.

The surface is held until you press Enter, so a fast command cannot erase its
own result. Pass `--no-fullscreen` (or set `TENXGRAPH_NO_FULLSCREEN=1`) to keep
everything in your normal scrollback instead — useful when you want to scroll
back or copy a path afterwards.

Long-running work reports through a live step timeline: stages are declared up
front, pending ones stay dimmed, and the running one animates with an elapsed
timer. `10xgraph eval` uses a determinate progress bar with a running pass/fail
tally.

Motion is disabled automatically for redirected output, CI, `TERM=dumb`,
JSON/JSONL, and `TENXGRAPH_NO_SPINNER=1`. Use `--no-animation` for a stable
screen-reader friendly experience, or `--animation` to force motion in a
compatible terminal. Every animated surface has a plain line-per-transition
renderer and a versioned JSON/JSONL event renderer.

### `10xgraph build`

Generate production Docker files.

```bash
10xgraph build                            # Dockerfile
10xgraph build --docker-compose           # Dockerfile + docker-compose.yml
10xgraph build --k8s                      # Dockerfile + k8s.yaml (Deployment + Service)
10xgraph build --python-version 3.12 --port 9000
10xgraph build --service-name my-agent    # name used in docker-compose.yml / k8s.yaml
10xgraph build --force                    # overwrite an existing Dockerfile
```

### `10xgraph eval` / `10xgraph test`

Run agent evaluations (discovers `*_eval.py` / `eval_*.py`, writes HTML + JSON to `eval_reports/`) and project tests (pytest).

```bash
10xgraph eval --parallel --threshold 0.8
10xgraph test --coverage
```

### `10xgraph skills`

Install bundled coding-agent skills (Codex, Claude, GitHub Copilot) into your project so your AI assistant knows how to build with 10xGraph.

```bash
10xgraph skills                # pick agents interactively (space toggles, enter confirms)
10xgraph skills --all          # install for every supported agent
10xgraph skills --agent claude # install for one
10xgraph skills --list         # show supported agents
10xgraph skills --force        # overwrite an existing install
10xgraph skills --validate ./.agents/skills  # check skills against the Agent Skills spec
```

Run without flags to get a checklist of the supported agents. Each row shows
where it installs, agents that are already set up are labelled and pre-checked,
and picking one that exists offers to overwrite rather than failing.

### `10xgraph version`

Display CLI and package version information.

```bash
10xgraph --version            # script-friendly CLI version only
10xgraph version
```

### `10xgraph audit`

Read-only check of everything that has to be true before `dev`, `eval`, or `build`
can work here: the Python interpreter, the installed `10xgraph-api` and
`10xgraph` packages, whether the installed core still exposes the
evaluation API this CLI imports, whether `10xgraph.json` is present and declares a
valid `agent` key, and whether the default port is free.

```bash
10xgraph audit                    # table of six checks
10xgraph --format json audit      # machine-readable, for CI
10xgraph --no-animation audit     # static output
```

Nothing is written or changed. It exits `1` if any check fails and `0` otherwise —
warnings (no project config, port already bound) are reported without failing the
run — so it works as a CI gate.

### `10xgraph config`

Open a local browser editor for `10xgraph.json`: switch optional sections (auth,
authorization, rate limiting, observability, ...) on or off, fill in their fields,
**Validate** without saving, and **Save** to write the file. Saving is blocked while
there are errors, and the previous file is kept as `10xgraph.json.bak`.

```bash
10xgraph config                           # edit ./10xgraph.json
10xgraph config -c path/to/10xgraph.json --port 8765 --no-open
```

### `10xgraph demo`

Preview the terminal animations and progress states without touching project state.

```bash
10xgraph demo                  # every theme
10xgraph demo --style eval     # one of: typing, network, init, build, eval
```

---

## ⚙️ Configuration

The configuration file (`10xgraph.json`) defines your agent, authentication, and infrastructure settings:

```json
{
  "agent": "graph.react:app",
  "env": ".env",
  "auth": null,
  "checkpointer": null,
  "injectq": null,
  "store": null,
  "remote_tools": [],
  "redis": null,
  "thread_name_generator": null,
  "rate_limit": {}
}
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `agent` | string | Path to your compiled agent graph, `"module:attribute"` (required) |
| `env` | string | Path to environment variables file |
| `auth` | null \| "jwt" \| object | Authentication configuration |
| `authorization` | string \| null | Path to an `AuthorizationBackend` (RBAC / per-tool access) |
| `checkpointer` | string \| null | Path to a custom checkpointer |
| `injectq` | string \| null | Path to an InjectQ container |
| `store` | string \| null | Path to a data store |
| `remote_tools` | array | Trusted schemas for tools executed by clients; attached at startup |
| `redis` | string \| null | Redis connection URL |
| `rate_limit` | object \| null | Sliding-window rate limiting configuration |
| `thread_name_generator` | string \| null | Path to a custom thread name generator |

See the **[Configuration Guide](./docs/configuration.md)** for complete details.

---

## 🔐 Authentication

10xGraph supports multiple authentication strategies. See the **[Authentication Guide](./docs/authentication.md)** for details.

### JWT Authentication

**10xgraph.json:**
```json
{ "auth": "jwt" }
```

**.env:**
```bash
JWT_SECRET_KEY=your-super-secret-key
JWT_ALGORITHM=HS256
```

### Custom Authentication

**10xgraph.json:**
```json
{ "auth": { "method": "custom", "path": "auth.custom:MyAuthBackend" } }
```

**auth/custom.py:**
```python
from tenxgraph_api import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class MyAuthBackend(BaseAuth):
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials,
    ) -> dict[str, any] | None:
        token = credential.credentials
        user = verify_token(token)
        if not user:
            raise HTTPException(401, "Invalid token")
        return {"user_id": user.id, "username": user.username, "email": user.email}
```

---

## 🆔 ID Generation

10xGraph includes Snowflake ID generation for distributed, time-sortable unique IDs.

```bash
pip install "10xgraph-api[snowflakekit]"
```

```python
from tenxgraph_api import SnowFlakeIdGenerator

generator = SnowFlakeIdGenerator(
    snowflake_epoch=1704067200000,  # Jan 1, 2024
    snowflake_node_id=1,
    snowflake_worker_id=1,
)
new_id = await generator.generate()
```

**Environment configuration:**
```bash
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
SNOWFLAKE_TIME_BITS=39
SNOWFLAKE_NODE_BITS=5
SNOWFLAKE_WORKER_BITS=8
```

See the **[ID Generation Guide](./docs/id-generation.md)** for more details.

---

## 🧵 Thread Name Generation

Generate human-friendly names for conversation threads.

```python
from tenxgraph_api.src.app.utils.thread_name_generator import AIThreadNameGenerator

generator = AIThreadNameGenerator()
name = generator.generate_name()
# "thoughtful-dialogue", "exploring-ideas", ...
```

See the **[Thread Name Generator Guide](./docs/thread-name-generator.md)** for custom implementations.

---

## 🛡️ Security

10xGraph CLI provides production-grade security features.

- ✅ **Authentication** - JWT and custom authentication backends
- ✅ **Authorization** - Resource-based access control with extensible backends
- ✅ **Request Limits** - DoS protection with configurable size limits (default 10MB)
- ✅ **Error Sanitization** - Production-safe error messages preventing information disclosure
- ✅ **Log Sanitization** - Automatic redaction of sensitive data (tokens, passwords, secrets)
- ✅ **Security Warnings** - Startup validation for insecure configurations
- ✅ **HTTPS Ready** - SSL/TLS support with secure headers

### Production Security Checklist

```bash
MODE=production                  # production mode
JWT_SECRET_KEY=<32+ chars>       # strong secret (secrets.token_urlsafe(32))
IS_DEBUG=false                   # disable debug
ORIGINS=https://yourdomain.com   # specific CORS origins (never *)
ALLOWED_HOST=yourdomain.com      # specific allowed hosts (never *)
DOCS_PATH=                       # recommended: disable API docs
REDOCS_PATH=
MAX_REQUEST_SIZE=10485760        # request size limit (10MB default)
```

For deployment hardening and authentication patterns, see the
**[Deployment Guide](./docs/deployment.md)** and **[Authentication Guide](./docs/authentication.md)**.

---

## 🐳 Deployment

See the **[Deployment Guide](./docs/deployment.md)** for full instructions.

```bash
# Generate Docker files
10xgraph build --docker-compose

# Build and run
docker compose up --build -d

# Check logs
docker compose logs -f
```

Cloud targets covered in the guide: [AWS ECS](./docs/deployment.md#aws-ecs),
[Google Cloud Run](./docs/deployment.md#google-cloud-run),
[Azure Container Instances](./docs/deployment.md#azure-container-instances),
[Kubernetes](./docs/deployment.md#kubernetes), and [Heroku](./docs/deployment.md#heroku).

---

## 📁 Project Structure

```
10xgraph-api/
├── tenxgraph_api/          # Main package
│   ├── __init__.py        # Package exports (BaseAuth, SnowFlakeIdGenerator, ThreadNameGenerator)
│   ├── cli/               # Typer CLI: main.py + commands/ + templates/
│   └── src/app/           # FastAPI application (main.py, loader.py, core/, routers/, utils/)
├── docs/                   # Documentation
├── tests/                  # Test suite
├── 10xgraph.json          # Configuration
├── pyproject.toml          # Project metadata
└── README.md               # This file
```

---

## 🔧 Development

```bash
# Clone and set up
git clone https://github.com/10xGraph/10xgraph-api.git
cd 10xgraph-api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Quality gate
pytest                                # tests (coverage gate: 80%)
pytest --cov=tenxgraph_api --cov-report=html
ruff check . && ruff format .         # lint + format
pre-commit run --all-files            # full gate (ruff + bandit, pinned versions)
```

### Using the Makefile

```bash
make build     # build sdist + wheel
make test      # run tests
make test-cov  # run tests with coverage
make publish   # upload to PyPI (maintainers)
make clean     # remove build artifacts
```

### Releasing

Releases are cut by pushing a version tag that matches `pyproject.toml`. The
[`release.yml`](./.github/workflows/release.yml) workflow then verifies the tag, builds the
sdist + wheel, checks the distribution metadata, and creates a GitHub Release with auto-generated
notes and the artifacts attached. PyPI publishing is manual (`make publish`).

```bash
git tag v0.3.2.9 && git push origin v0.3.2.9
```

---

## 📄 License

10xGraph is [MIT licensed](https://github.com/10xGraph/10xgraph-api/blob/main/LICENSE) and made by
[10xScale](https://10xscale.ai). Contributions are accepted under the same license.

---

## 🔗 Links & Resources

- **[Documentation](https://10xgraph.com/)** - Full framework docs
- **[Core framework (`10xgraph`)](https://github.com/10xGraph/10xgraph)** - The orchestration engine this CLI serves
- **[This repository](https://github.com/10xGraph/10xgraph-api)** - Source code and issues
- **[PyPI Project](https://pypi.org/project/10xgraph-api/)** - Package releases (final release: `0.6.0`)
- **[10xGraph](https://10xgraph.com)** and **[github.com/10xGraph](https://github.com/10xGraph)** - Where development continues
- **[Local docs](./docs/)** - CLI, configuration, deployment, auth, rate limiting, IDs, thread names

---

## 🙏 Contributing

Contributions are welcome! Fork the repo, create a feature branch, run tests and linting, and open a
Pull Request. See the [repository](https://github.com/10xGraph/10xgraph-api) for issue reporting and
guidelines.

---

## 💬 Support

- **Documentation:** [10xgraph.com](https://10xgraph.com/) and [local docs](./docs/)
- **Issues:** [GitHub Issues](https://github.com/10xGraph/10xgraph-api/issues)
- **Repository:** [GitHub](https://github.com/10xGraph/10xgraph-api)

---

Developed by [10xScale](https://10xscale.ai) and maintained by the community. New projects should
start on [10xGraph](https://github.com/10xGraph).

**Made with ❤️ for the AI agent development community**
