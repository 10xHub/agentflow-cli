# AgentFlow CLI

A professional Python API framework for building agent-based applications with FastAPI, state graph orchestration, and comprehensive CLI tools.

## 📚 Documentation

- **[CLI Guide](./docs/cli-guide.md)** - Complete command-line interface reference
- **[Configuration Guide](./docs/configuration.md)** - All configuration options explained
- **[Deployment Guide](./docs/deployment.md)** - Docker, Kubernetes, and cloud deployment
- **[Authentication Guide](./docs/authentication.md)** - JWT and custom authentication
- **[ID Generation Guide](./docs/id-generation.md)** - Snowflake ID generation
- **[Thread Name Generator Guide](./docs/thread-name-generator.md)** - Thread naming strategies

## Quick Start

### Installation

```bash
pip install 10xscale-agentflow-cli
```

### Initialize a New Project

```bash
# Create project structure
agentflow init

# Or with production config
agentflow init --prod
```

### Start Development Server

```bash
agentflow api
```

### Generate Docker Files

```bash
agentflow build --docker-compose
```

## Key Features

- ✅ **CLI Tools** - Professional command-line interface for scaffolding and deployment
- ✅ **State Graph Orchestration** - Build complex agent workflows with LangGraph
- ✅ **FastAPI Backend** - High-performance async web framework
- ✅ **Authentication** - Built-in JWT auth and custom authentication support
- ✅ **ID Generation** - Distributed Snowflake ID generation
- ✅ **Thread Management** - Intelligent thread naming and conversation management
- ✅ **Docker Ready** - Generate production-ready Docker files
- ✅ **Dependency Injection** - InjectQ for clean dependency management
- ✅ **Development Tools** - Hot-reload, pre-commit hooks, testing

## CLI Commands

For detailed command documentation, see the [CLI Guide](./docs/cli-guide.md).

### `agentflow init`

Initialize a new project with configuration and sample graph.

```bash
# Basic initialization
agentflow init

# With production config (pyproject.toml, pre-commit hooks)
agentflow init --prod

# Custom directory
agentflow init --path ./my-project

# Force overwrite existing files
agentflow init --force
```

### `agentflow api`

Start the development API server.

```bash
# Start with defaults (localhost:8000)
agentflow api

# Custom host and port
agentflow api --host 127.0.0.1 --port 9000

# Custom config file
agentflow api --config production.json

# Disable auto-reload
agentflow api --no-reload

# Verbose logging
agentflow api --verbose
```

### `agentflow build`

Generate production Docker files.

```bash
# Generate Dockerfile
agentflow build

# Generate Dockerfile and docker-compose.yml
agentflow build --docker-compose

# Custom Python version and port
agentflow build --python-version 3.12 --port 9000

# Force overwrite
agentflow build --force
```

### `agentflow version`

Display version information.

```bash
agentflow version
```

## Configuration

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
  "thread_name_generator": null
}
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `agent` | string | Path to your compiled agent graph (required) |
| `env` | string | Path to environment variables file |
| `auth` | null\|"jwt"\|object | Authentication configuration |
| `checkpointer` | string\|null | Path to custom checkpointer |
| `injectq` | string\|null | Path to InjectQ container |
| `store` | string\|null | Path to data store |
| `redis` | string\|null | Redis connection URL |
| `thread_name_generator` | string\|null | Path to custom thread name generator |

See the [Configuration Guide](./docs/configuration.md) for complete details.

## Authentication

AgentFlow supports multiple authentication strategies. See the [Authentication Guide](./docs/authentication.md) for complete details.

### No Authentication

```json
{
  "auth": null
}
```

### JWT Authentication

**agentflow.json:**
```json
{
  "auth": "jwt"
}
```

**.env:**
```bash
JWT_SECRET_KEY=your-super-secret-key
JWT_ALGORITHM=HS256
```

### Custom Authentication

**agentflow.json:**
```json
{
  "auth": {
    "method": "custom",
    "path": "auth.custom:MyAuthBackend"
  }
}
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
        credential: HTTPAuthorizationCredentials
    ) -> dict[str, any] | None:
        # Your authentication logic
        token = credential.credentials
        user = verify_token(token)

        if not user:
            raise HTTPException(401, "Invalid token")

        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }
```

## ID Generation

AgentFlow includes Snowflake ID generation for distributed, time-sortable unique IDs.

```bash
pip install "10xscale-agentflow-cli[snowflakekit]"
```

**Usage:**
```python
from agentflow_cli import SnowFlakeIdGenerator

# Initialize
generator = SnowFlakeIdGenerator(
    snowflake_epoch=1704067200000,  # Jan 1, 2024
    snowflake_node_id=1,
    snowflake_worker_id=1
)

# Generate ID
id = await generator.generate()
print(f"Generated ID: {id}")
```

**Environment Configuration:**
```bash
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
SNOWFLAKE_TIME_BITS=39
SNOWFLAKE_NODE_BITS=5
SNOWFLAKE_WORKER_BITS=8
```

See the [ID Generation Guide](./docs/id-generation.md) for more details.

## Thread Name Generation

Generate human-friendly names for conversation threads.

```python
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator

generator = AIThreadNameGenerator()
name = generator.generate_name()
# Output: "thoughtful-dialogue", "exploring-ideas", etc.
```

See the [Thread Name Generator Guide](./docs/thread-name-generator.md) for custom implementations.
## Deployment

See the [Deployment Guide](./docs/deployment.md) for complete deployment instructions.

### Docker Deployment

```bash
# Generate Docker files
agentflow build --docker-compose

# Build and run
docker compose up --build -d

# Check logs
docker compose logs -f
```

### Kubernetes

See [Deployment Guide - Kubernetes](./docs/deployment.md#kubernetes) for complete manifests.

### Cloud Platforms

- [AWS ECS](./docs/deployment.md#aws-ecs)
- [Google Cloud Run](./docs/deployment.md#google-cloud-run)
- [Azure Container Instances](./docs/deployment.md#azure-container-instances)
- [Heroku](./docs/deployment.md#heroku)

## Project Structure

```
agentflow-cli/
├── agentflow_cli/          # Main package
│   ├── __init__.py        # Package exports
│   ├── cli/               # CLI commands
│   │   ├── main.py       # CLI entry point
│   │   └── commands/     # Command implementations
│   └── src/              # Application source
│       └── app/          # FastAPI application
│           ├── main.py   # App entry point
│           ├── core/     # Core functionality
│           ├── routers/  # API routes
│           └── utils/    # Utilities
├── graph/                 # Agent graphs
│   ├── __init__.py
│   └── react.py          # Sample React agent
├── docs/                  # Documentation
├── tests/                 # Test suite
├── agentflow.json        # Configuration
├── pyproject.toml        # Project metadata
└── README.md             # This file
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/10xHub/agentflow-cli.git
cd agentflow-cli

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=agentflow_cli --cov-report=html

# Run specific test file
pytest tests/test_cli.py -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Using the Makefile

```bash
# Show available commands
make help

# Install development dependencies
make dev-install

# Run tests
make test

# Format and lint
make format
make lint

# Build package
make build

# Clean build artifacts
make clean
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation:** [Complete Documentation](./docs/)
- **Issues:** [GitHub Issues](https://github.com/10xHub/agentflow-cli/issues)
- **Repository:** [GitHub](https://github.com/10xHub/agentflow-cli)

## Credits

Developed by [10xScale](https://10xscale.ai) and maintained by the community.

---

**Made with ❤️ for the AI agent development community**

