
# 10xScale Agentflow CLI

[![CI](https://github.com/10xHub/agentflow-cli/actions/workflows/ci.yaml/badge.svg)](https://github.com/10xHub/agentflow-cli/actions/workflows/ci.yaml)
[![Release](https://github.com/10xHub/agentflow-cli/actions/workflows/release.yml/badge.svg)](https://github.com/10xHub/agentflow-cli/actions/workflows/release.yml)

[![PyPI](https://img.shields.io/pypi/v/10xscale-agentflow-cli?color=blue)](https://pypi.org/project/10xscale-agentflow-cli/)
[![Python](https://img.shields.io/pypi/pyversions/10xscale-agentflow-cli)](https://pypi.org/project/10xscale-agentflow-cli/)
[![License](https://img.shields.io/github/license/10xHub/agentflow-cli)](https://github.com/10xHub/agentflow-cli/blob/main/LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/10xHub/agentflow-cli/actions/workflows/ci.yaml)
[![Tests](https://img.shields.io/badge/tests-871%20passed-brightgreen.svg)](https://github.com/10xHub/agentflow-cli/actions/workflows/ci.yaml)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://pypi.org/project/10xscale-agentflow-cli/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**10xScale Agentflow CLI** turns an Agentflow `CompiledGraph` into a production-grade FastAPI service, plus a Typer-based command line to scaffold, run, build, test, and evaluate it. You write a graph, point `agentflow.json` at it, and `agentflow api` serves it over REST + WebSocket with authentication, rate limiting, media handling, checkpointer/thread management, and a memory store API.

> ### 📦 Part of the 10xScale Agentflow library
>
> This package (`10xscale-agentflow-cli`) is the **API server + CLI layer** of the larger
> [**10xScale Agentflow**](https://github.com/10xHub/agentflow) framework. The core orchestration
> engine — `StateGraph`, `Agent`, `ToolNode`, state, persistence, memory, and tools — lives in the
> separate [`10xscale-agentflow`](https://pypi.org/project/10xscale-agentflow/) package. This CLI
> builds on top of it to expose your agent graphs as a deployable service.
>
> - **Core framework:** [`10xscale-agentflow`](https://pypi.org/project/10xscale-agentflow/) · [source](https://github.com/10xHub/agentflow)
> - **This package (API + CLI):** [`10xscale-agentflow-cli`](https://pypi.org/project/10xscale-agentflow-cli/)
> - **TypeScript client:** [`@10xscale/agentflow-client`](https://www.npmjs.com/package/@10xscale/agentflow-client)
> - **Docs:** [agentflow.10xscale.ai](https://agentflow.10xscale.ai/)

---

## ✨ Key Features

- **🖥️ Professional CLI** - Scaffold, run, build, test, and evaluate agents from one command line
- **⚡ FastAPI Backend** - Your compiled graph auto-served over REST + WebSocket, high-performance and async
- **🔌 Config-Driven** - One `agentflow.json` wires agent, auth, checkpointer, store, Redis, and rate limits
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
pip install 10xscale-agentflow-cli
```

Optional extras — install only what you configure:

```bash
pip install "10xscale-agentflow-cli[redis]"   # Redis rate-limit / cache backend
pip install "10xscale-agentflow-cli[jwt]"     # JWT authentication
pip install "10xscale-agentflow-cli[media]"   # Document text extraction (multimodal)
pip install "10xscale-agentflow-cli[otel]"    # OpenTelemetry tracing
pip install "10xscale-agentflow-cli[snowflakekit]"  # Snowflake ID generation
```

Requires **Python ≥ 3.12**. Depends on the core `10xscale-agentflow` framework.

---

## 🚀 Quick Start

```bash
# 1. Scaffold a project (interactive: dev vs production, auth, rate limiting)
agentflow init

# 2. Start the dev API server (127.0.0.1:8000)
agentflow api

# 3. Or start the server and open the hosted playground
agentflow play

# 4. Generate production Docker files
agentflow build --docker-compose
```

---

## 🖥️ CLI Commands

For detailed command documentation, see the **[CLI Guide](./docs/cli-guide.md)**.

### `agentflow init`

Initialize a new project with configuration and a sample graph.

```bash
agentflow init                  # interactive (chooses dev vs production setup)
agentflow init --path ./my-app  # custom directory
agentflow init --force          # overwrite existing files
```

### `agentflow api`

Start the development API server.

```bash
agentflow api                              # defaults (127.0.0.1:8000)
agentflow api --host 127.0.0.1 --port 9000 # custom host/port
agentflow api --config production.json     # custom config file
agentflow api --no-reload                  # disable auto-reload
agentflow api --verbose                    # verbose logging
```

### `agentflow play`

Start the dev server and open the hosted playground with your local backend URL preconfigured.

```bash
agentflow play
agentflow play --host 127.0.0.1 --port 9000
agentflow play --config production.json
```

### `agentflow build`

Generate production Docker files.

```bash
agentflow build                            # Dockerfile
agentflow build --docker-compose           # Dockerfile + docker-compose.yml
agentflow build --python-version 3.12 --port 9000
agentflow build --force
```

### `agentflow eval` / `agentflow test`

Run agent evaluations (discovers `*_eval.py` / `eval_*.py`, writes HTML + JSON to `eval_reports/`) and project tests (pytest).

```bash
agentflow eval --parallel --threshold 0.8
agentflow test --coverage
```

### `agentflow skills`

Install bundled coding-agent skills (Codex, Claude, GitHub Copilot) into your project so your AI assistant knows how to build with Agentflow.

```bash
agentflow skills --all          # install for every supported agent
agentflow skills --agent claude # install for one
agentflow skills --list         # show supported agents
```

### `agentflow version`

Display CLI and package version information.

```bash
agentflow version
```

---

## ⚙️ Configuration

The configuration file (`agentflow.json`) defines your agent, authentication, and infrastructure settings:

```json
{
  "agent": "graph.react:app",
  "env": ".env",
  "auth": null,
  "checkpointer": null,
  "injectq": null,
  "store": null,
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
| `redis` | string \| null | Redis connection URL |
| `rate_limit` | object \| null | Sliding-window rate limiting configuration |
| `thread_name_generator` | string \| null | Path to a custom thread name generator |

See the **[Configuration Guide](./docs/configuration.md)** for complete details.

---

## 🔐 Authentication

Agentflow supports multiple authentication strategies. See the **[Authentication Guide](./docs/authentication.md)** for details.

### JWT Authentication

**agentflow.json:**
```json
{ "auth": "jwt" }
```

**.env:**
```bash
JWT_SECRET_KEY=your-super-secret-key
JWT_ALGORITHM=HS256
```

### Custom Authentication

**agentflow.json:**
```json
{ "auth": { "method": "custom", "path": "auth.custom:MyAuthBackend" } }
```

**auth/custom.py:**
```python
from agentflow_cli import BaseAuth
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

Agentflow includes Snowflake ID generation for distributed, time-sortable unique IDs.

```bash
pip install "10xscale-agentflow-cli[snowflakekit]"
```

```python
from agentflow_cli import SnowFlakeIdGenerator

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
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator

generator = AIThreadNameGenerator()
name = generator.generate_name()
# "thoughtful-dialogue", "exploring-ideas", ...
```

See the **[Thread Name Generator Guide](./docs/thread-name-generator.md)** for custom implementations.

---

## 🛡️ Security

Agentflow CLI provides production-grade security features.

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
agentflow build --docker-compose

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
agentflow-cli/
├── agentflow_cli/          # Main package
│   ├── __init__.py        # Package exports (BaseAuth, SnowFlakeIdGenerator, ThreadNameGenerator)
│   ├── cli/               # Typer CLI: main.py + commands/ + templates/
│   └── src/app/           # FastAPI application (main.py, loader.py, core/, routers/, utils/)
├── docs/                   # Documentation
├── tests/                  # Test suite
├── agentflow.json          # Configuration
├── pyproject.toml          # Project metadata
└── README.md               # This file
```

---

## 🔧 Development

```bash
# Clone and set up
git clone https://github.com/10xHub/agentflow-cli.git
cd agentflow-cli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install

# Quality gate
pytest                                # tests (coverage gate: 80%)
pytest --cov=agentflow_cli --cov-report=html
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

MIT License - see [LICENSE](https://github.com/10xHub/agentflow-cli/blob/main/LICENSE) for details.

---

## 🔗 Links & Resources

- **[Documentation](https://agentflow.10xscale.ai/)** - Full framework docs
- **[Core framework (`10xscale-agentflow`)](https://github.com/10xHub/agentflow)** - The orchestration engine this CLI serves
- **[This repository](https://github.com/10xHub/agentflow-cli)** - Source code and issues
- **[PyPI Project](https://pypi.org/project/10xscale-agentflow-cli/)** - Package releases
- **[Local docs](./docs/)** - CLI, configuration, deployment, auth, rate limiting, IDs, thread names

---

## 🙏 Contributing

Contributions are welcome! Fork the repo, create a feature branch, run tests and linting, and open a
Pull Request. See the [repository](https://github.com/10xHub/agentflow-cli) for issue reporting and
guidelines.

---

## 💬 Support

- **Documentation:** [agentflow.10xscale.ai](https://agentflow.10xscale.ai/) and [local docs](./docs/)
- **Issues:** [GitHub Issues](https://github.com/10xHub/agentflow-cli/issues)
- **Repository:** [GitHub](https://github.com/10xHub/agentflow-cli)

---

Developed by [10xScale](https://10xscale.ai) and maintained by the community.

**Made with ❤️ for the AI agent development community**
