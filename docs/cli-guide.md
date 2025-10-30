# AgentFlow CLI - Complete Guide

The `agentflow` CLI is a professional command-line interface for scaffolding, running, and deploying agent-based APIs built with the AgentFlow framework.

## Installation

```bash
pip install 10xscale-agentflow-cli
```

For development with all optional dependencies:

```bash
pip install "10xscale-agentflow-cli[redis,sentry,firebase,snowflakekit,gcloud]"
```

## Quick Start

```bash
# Initialize a new project
agentflow init

# Start development server
agentflow api

# Generate Dockerfile
agentflow build
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `agentflow init` | Initialize a new project with config and graph scaffold |
| `agentflow api` | Start the development API server |
| `agentflow build` | Generate Docker deployment files |
| `agentflow version` | Display CLI and package versions |

---

## `agentflow init`

Initialize a new AgentFlow project with configuration and sample graph code.

### Synopsis

```bash
agentflow init [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--path`, `-p` | STRING | `.` | Directory to initialize files in |
| `--force`, `-f` | FLAG | `False` | Overwrite existing files |
| `--prod` | FLAG | `False` | Include production configuration files |
| `--verbose`, `-v` | FLAG | `False` | Enable verbose logging |
| `--quiet`, `-q` | FLAG | `False` | Suppress all output except errors |

### Behavior

**Default Mode:**
- Creates `agentflow.json` configuration file
- Creates `graph/react.py` with a sample React-based agent
- Creates `graph/__init__.py` to make it a Python package

**Production Mode (`--prod`):**
- All default files plus:
  - `.pre-commit-config.yaml` - Pre-commit hooks configuration
  - `pyproject.toml` - Python project metadata and tooling config

### Examples

**Basic initialization:**
```bash
agentflow init
```

**Initialize in a specific directory:**
```bash
agentflow init --path ./my-agent-project
```

**Initialize with production config:**
```bash
agentflow init --prod
```

**Overwrite existing files:**
```bash
agentflow init --force
```

**Initialize production project in a new directory:**
```bash
agentflow init --prod --path ./production-agent --force
cd production-agent
pre-commit install
```

### Generated Files

#### `agentflow.json`
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

#### `graph/react.py`
A fully-commented sample agent implementation featuring:
- LiteLLM integration for AI completion
- Tool definition and execution
- State graph orchestration
- Conditional routing
- In-memory checkpointer

---

## `agentflow api`

Start the AgentFlow API development server with hot-reload support.

### Synopsis

```bash
agentflow api [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config`, `-c` | STRING | `agentflow.json` | Path to configuration file |
| `--host`, `-H` | STRING | `0.0.0.0` | Host to bind the server to |
| `--port`, `-p` | INTEGER | `8000` | Port to bind the server to |
| `--reload` / `--no-reload` | FLAG | `True` | Enable/disable auto-reload |
| `--verbose`, `-v` | FLAG | `False` | Enable verbose logging |
| `--quiet`, `-q` | FLAG | `False` | Suppress all output except errors |

### Behavior

1. Loads the specified configuration file
2. Loads environment variables from `.env` file (or file specified in config)
3. Sets `GRAPH_PATH` environment variable
4. Starts Uvicorn server with specified host and port
5. Watches for file changes and auto-reloads (if `--reload` is enabled)

### Examples

**Start with default settings:**
```bash
agentflow api
```

**Start with custom config file:**
```bash
agentflow api --config production.json
```

**Start on localhost only:**
```bash
agentflow api --host 127.0.0.1
```

**Start on custom port:**
```bash
agentflow api --port 9000
```

**Start without auto-reload (for testing):**
```bash
agentflow api --no-reload
```

**Start with verbose logging:**
```bash
agentflow api --verbose
```

**Combine multiple options:**
```bash
agentflow api --config staging.json --host 127.0.0.1 --port 8080 --verbose
```

### Server Access

Once started, the API is accessible at:
- **Default:** `http://0.0.0.0:8000`
- **Local access:** `http://localhost:8000`
- **Network access:** `http://<your-ip>:8000`

### API Endpoints

The server provides several endpoints:
- `GET /ping` - Health check endpoint
- `POST /threads` - Create a new thread
- `GET /threads/{thread_id}` - Get thread details
- `POST /threads/{thread_id}/messages` - Send a message
- `GET /threads/{thread_id}/messages` - Get thread messages

### Development Workflow

```bash
# 1. Initialize project
agentflow init

# 2. Create .env file with your API keys
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. Start development server
agentflow api --verbose

# 4. Test the API
curl http://localhost:8000/ping

# 5. Make changes to your graph - server auto-reloads
```

---

## `agentflow build`

Generate production-ready Docker deployment files.

### Synopsis

```bash
agentflow build [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output`, `-o` | STRING | `Dockerfile` | Output Dockerfile path |
| `--force`, `-f` | FLAG | `False` | Overwrite existing files |
| `--python-version` | STRING | `3.13` | Python version for base image |
| `--port`, `-p` | INTEGER | `8000` | Port to expose in container |
| `--docker-compose` | FLAG | `False` | Also generate docker-compose.yml |
| `--service-name` | STRING | `agentflow-cli` | Service name in docker-compose |
| `--verbose`, `-v` | FLAG | `False` | Enable verbose logging |
| `--quiet`, `-q` | FLAG | `False` | Suppress all output except errors |

### Behavior

1. Searches for `requirements.txt` in common locations:
   - `./requirements.txt`
   - `./requirements/requirements.txt`
   - `./requirements/base.txt`
   - `./requirements/production.txt`
2. Generates optimized Dockerfile with:
   - Multi-stage build support
   - Non-root user for security
   - Health check configuration
   - Gunicorn + Uvicorn workers
3. Optionally generates `docker-compose.yml`

### Examples

**Generate basic Dockerfile:**
```bash
agentflow build
```

**Generate with custom Python version:**
```bash
agentflow build --python-version 3.12
```

**Generate with custom port:**
```bash
agentflow build --port 9000
```

**Generate Dockerfile and docker-compose.yml:**
```bash
agentflow build --docker-compose
```

**Complete production setup:**
```bash
agentflow build --docker-compose --python-version 3.13 --port 8000 --force
```

**Custom service name in docker-compose:**
```bash
agentflow build --docker-compose --service-name my-agent-api
```

### Generated Dockerfile Features

- **Base Image:** Python slim image for reduced size
- **Security:** Non-root user execution
- **Optimization:** Multi-layer caching for faster builds
- **Health Check:** Built-in `/ping` endpoint monitoring
- **Production Server:** Gunicorn with Uvicorn workers

### Docker Build and Run

After generating the Dockerfile:

```bash
# Build the image
docker build -t my-agent-api .

# Run the container
docker run -p 8000:8000 --env-file .env my-agent-api

# Or use docker-compose
docker compose up --build
```

---

## `agentflow version`

Display version information for the CLI and installed packages.

### Synopsis

```bash
agentflow version [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verbose`, `-v` | FLAG | `False` | Show additional version details |
| `--quiet`, `-q` | FLAG | `False` | Show only version number |

### Examples

```bash
# Show version
agentflow version

# Verbose output with dependencies
agentflow version --verbose
```

---

## Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message and exit |
| `--verbose`, `-v` | Enable verbose logging output |
| `--quiet`, `-q` | Suppress all output except errors |

### Examples

```bash
# Get help for any command
agentflow init --help
agentflow api --help
agentflow build --help

# Run with verbose output
agentflow api --verbose
agentflow build --verbose
```

---

## Configuration File Resolution

The CLI searches for configuration files in this order:

1. **Explicit path:** If you provide `--config /path/to/config.json`, it uses that
2. **Current directory:** Looks for `agentflow.json` in current working directory
3. **Relative to script:** Searches relative to the CLI installation
4. **Package directory:** Falls back to package installation location

---

## Environment Variables

The CLI respects these environment variables:

| Variable | Purpose | Used By |
|----------|---------|---------|
| `GRAPH_PATH` | Path to active config file | API server |
| `GEMINI_API_KEY` | API key for Gemini models | LiteLLM |
| `OPENAI_API_KEY` | API key for OpenAI models | LiteLLM |
| `JWT_SECRET_KEY` | Secret key for JWT auth | Auth system |
| `JWT_ALGORITHM` | Algorithm for JWT (e.g., HS256) | Auth system |
| `SNOWFLAKE_*` | Snowflake ID generator config | ID generation |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Validation error |
| `130` | Interrupted by user (Ctrl+C) |

---

## Common Workflows

### Starting a New Project

```bash
# 1. Initialize with production config
agentflow init --prod

# 2. Install pre-commit hooks
pre-commit install

# 3. Create environment file
cat > .env << EOF
GEMINI_API_KEY=your_api_key_here
LOG_LEVEL=INFO
EOF

# 4. Install dependencies
pip install -e ".[redis,sentry]"

# 5. Start development server
agentflow api --verbose
```

### Development Workflow

```bash
# Start server with auto-reload
agentflow api --reload --verbose

# In another terminal, test the API
curl http://localhost:8000/ping

# Make changes to graph/react.py
# Server automatically reloads
```

### Production Deployment

```bash
# 1. Generate Docker files
agentflow build --docker-compose --force

# 2. Review generated files
cat Dockerfile
cat docker-compose.yml

# 3. Build and test locally
docker compose up --build

# 4. Push to registry
docker tag agentflow-cli:latest registry.example.com/agentflow:latest
docker push registry.example.com/agentflow:latest

# 5. Deploy to production
kubectl apply -f k8s/deployment.yaml
```

### Testing Different Configurations

```bash
# Test with different config files
agentflow api --config dev.json --port 8001 &
agentflow api --config staging.json --port 8002 &
agentflow api --config prod.json --port 8003 &

# Test each endpoint
curl http://localhost:8001/ping
curl http://localhost:8002/ping
curl http://localhost:8003/ping
```

---

## Troubleshooting

### Server won't start

**Problem:** `Error loading graph from graph.react:app`

**Solution:**
```bash
# Ensure your graph directory is a Python package
touch graph/__init__.py

# Verify your PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check your config file
cat agentflow.json
```

### Port already in use

**Problem:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
agentflow api --port 8001
```

### Config file not found

**Problem:** `ConfigurationError: Config file not found`

**Solution:**
```bash
# Check current directory
ls -la agentflow.json

# Use explicit path
agentflow api --config /full/path/to/agentflow.json

# Or initialize a new config
agentflow init
```

### Requirements not found during build

**Problem:** `No requirements.txt found`

**Solution:**
```bash
# Create requirements.txt
pip freeze > requirements.txt

# Or let build use default installation
agentflow build  # Will install agentflow-cli from PyPI
```

---

## Best Practices

### Development

1. **Use verbose logging** during development:
   ```bash
   agentflow api --verbose
   ```

2. **Keep auto-reload enabled** for faster iteration:
   ```bash
   agentflow api --reload
   ```

3. **Use localhost for local-only access**:
   ```bash
   agentflow api --host 127.0.0.1
   ```

### Production

1. **Disable auto-reload** in production:
   ```bash
   agentflow api --no-reload
   ```

2. **Use environment-specific configs**:
   ```bash
   agentflow api --config production.json
   ```

3. **Run behind a reverse proxy** (nginx, Traefik):
   ```bash
   # Bind to localhost only
   agentflow api --host 127.0.0.1 --port 8000
   ```

4. **Use Docker for consistent deployments**:
   ```bash
   agentflow build --docker-compose --force
   docker compose up -d
   ```

### Security

1. **Never commit `.env` files** - add to `.gitignore`
2. **Use different secrets per environment**
3. **Run containers as non-root user** (Dockerfile does this automatically)
4. **Keep dependencies updated**:
   ```bash
   pip install --upgrade 10xscale-agentflow-cli
   ```

---

## Additional Resources

- [Configuration Guide](./configuration.md) - Complete configuration reference
- [Deployment Guide](./deployment.md) - Production deployment strategies
- [Authentication Guide](./authentication.md) - Setting up auth
- [API Reference](./api-reference.md) - Complete API documentation

---

## Getting Help

```bash
# Command-specific help
agentflow init --help
agentflow api --help
agentflow build --help

# Check version
agentflow version

# Visit documentation
# https://agentflow-cli.readthedocs.io/
```
