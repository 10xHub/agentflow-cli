# Configuration Reference

This document provides a complete reference for configuring your AgentFlow application through `agentflow.json` and environment variables.

## Table of Contents

- [Configuration File](#configuration-file)
- [Core Configuration](#core-configuration)
- [Authentication](#authentication)
- [Dependency Injection](#dependency-injection)
- [Storage & Persistence](#storage--persistence)
- [Environment Variables](#environment-variables)
- [Application Settings](#application-settings)
- [Examples](#examples)

---

## Configuration File

### Location

The configuration file is typically named `agentflow.json` and should be placed in your project root. You can specify a custom location:

```bash
agentflow api --config /path/to/config.json
```

### File Resolution Order

1. Explicit path provided via `--config` flag
2. Current working directory
3. Relative to CLI installation
4. Package directory

### Basic Structure

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

---

## Core Configuration

### `agent` (Required)

Path to your compiled agent graph.

**Format:** `module.path:variable_name`

**Example:**
```json
{
  "agent": "graph.react:app"
}
```

This resolves to:
```python
# graph/react.py
from agentflow.graph import StateGraph

graph = StateGraph()
# ... graph configuration ...
app = graph.compile()
```

**Multiple Graphs:**
```json
{
  "agent": "graph.customer_service:support_agent"
}
```

```python
# graph/customer_service.py
support_agent = graph.compile(checkpointer=checkpointer)
```

### `env`

Path to environment variables file.

**Type:** `string | null`

**Default:** `.env`

**Examples:**
```json
// Use default .env file
{
  "env": ".env"
}

// Use environment-specific file
{
  "env": ".env.production"
}

// Multiple environment files
{
  "env": ".env.local"  // This will be loaded
}

// Disable env file loading
{
  "env": null
}
```

**Best Practice:**
```bash
# Development
.env.development

# Staging
.env.staging

# Production
.env.production
```

---

## Authentication

### `auth`

Configure authentication for your API.

**Type:** `null | "jwt" | { "method": "custom", "path": "module:class" }`

### No Authentication

```json
{
  "auth": null
}
```

### JWT Authentication

```json
{
  "auth": "jwt"
}
```

**Required Environment Variables:**
```bash
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
```

**Supported Algorithms:**
- HS256 (HMAC with SHA-256)
- HS384 (HMAC with SHA-384)
- HS512 (HMAC with SHA-512)
- RS256 (RSA with SHA-256)
- RS384 (RSA with SHA-384)
- RS512 (RSA with SHA-512)
- ES256 (ECDSA with SHA-256)
- ES384 (ECDSA with SHA-384)
- ES512 (ECDSA with SHA-512)

### Custom Authentication

```json
{
  "auth": {
    "method": "custom",
    "path": "auth.custom:CustomAuthBackend"
  }
}
```

**Implementation:**
```python
# auth/custom.py
from agentflow_cli import BaseAuth
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials

class CustomAuthBackend(BaseAuth):
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict[str, any] | None:
        """
        Authenticate the user based on credentials.
        
        Returns:
            dict with user info including 'user_id', or None if auth fails
        """
        token = credential.credentials
        
        # Your custom authentication logic
        user = verify_custom_token(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        }
```

**See also:** [Authentication Guide](./authentication.md)

---

## Dependency Injection

### `injectq`

Path to custom InjectQ container for dependency injection.

**Type:** `string | null`

**Format:** `module.path:container_instance`

**Example:**
```json
{
  "injectq": "app.container:container"
}
```

**Implementation:**
```python
# app/container.py
from injectq import InjectQ
from redis import Redis

container = InjectQ()

# Bind services
container.bind_instance(Redis, Redis(host='localhost', port=6379))

# Bind configurations
container.bind_instance(dict, {"api_key": "xxx"}, name="config")
```

**Default Behavior:**
If not specified, AgentFlow creates a default container with:
- GraphConfig instance
- BaseAuth (if configured)
- ThreadNameGenerator (if configured)

---

## Storage & Persistence

### `checkpointer`

Path to checkpointer for conversation state persistence.

**Type:** `string | null`

**Format:** `module.path:checkpointer_instance`

**Example:**
```json
{
  "checkpointer": "storage.checkpointer:redis_checkpointer"
}
```

**Implementation:**
```python
# storage/checkpointer.py
from agentflow.checkpointer import RedisCheckpointer

redis_checkpointer = RedisCheckpointer(
    redis_url="redis://localhost:6379",
    ttl=3600  # 1 hour
)
```

**Built-in Checkpointers:**
- `InMemoryCheckpointer` - For development/testing
- `RedisCheckpointer` - For production with Redis
- `PostgresCheckpointer` - For PostgreSQL storage

### `store`

Path to store for additional data persistence.

**Type:** `string | null`

**Format:** `module.path:store_instance`

**Example:**
```json
{
  "store": "storage.store:redis_store"
}
```

**Implementation:**
```python
# storage/store.py
from agentflow.store import RedisStore

redis_store = RedisStore(
    redis_url="redis://localhost:6379"
)
```

### `redis`

Redis connection URL for caching and sessions.

**Type:** `string | null`

**Format:** `redis://[username:password@]host:port[/database]`

**Examples:**
```json
// Local Redis
{
  "redis": "redis://localhost:6379"
}

// With authentication
{
  "redis": "redis://user:password@redis-host:6379"
}

// Specific database
{
  "redis": "redis://localhost:6379/1"
}

// Redis Cluster
{
  "redis": "redis://node1:6379,node2:6379,node3:6379"
}

// Use environment variable
{
  "redis": "${REDIS_URL}"
}
```

**Environment Variable:**
```bash
REDIS_URL=redis://localhost:6379
```

---

## Thread Name Generation

### `thread_name_generator`

Path to custom thread name generator.

**Type:** `string | null`

**Format:** `module.path:generator_class`

**Example:**
```json
{
  "thread_name_generator": "utils.naming:CustomNameGenerator"
}
```

**Implementation:**
```python
# utils/naming.py
from agentflow_cli import ThreadNameGenerator

class CustomNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Generate a custom thread name from messages."""
        # Custom logic here
        return f"thread-{uuid.uuid4().hex[:8]}"
```

**Default Behavior:**
If not specified, the system uses `AIThreadNameGenerator` which generates names like:
- `thoughtful-dialogue`
- `exploring-ideas`
- `deep-dive`

**See also:** [Thread Name Generator Guide](./thread-name-generator.md)

---

## Environment Variables

### Core Variables

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `GRAPH_PATH` | string | Path to agentflow.json | Set by CLI |
| `ENVIRONMENT` | string | Environment name | `development` |
| `LOG_LEVEL` | string | Logging level | `INFO` |
| `DEBUG` | boolean | Debug mode | `false` |

### Application Settings

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `APP_NAME` | string | Application name | `MyApp` |
| `APP_VERSION` | string | Application version | `0.1.0` |
| `MODE` | string | Running mode | `development` |
| `SUMMARY` | string | API summary | `Pyagenity Backend` |

### Server Settings

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `ORIGINS` | string | CORS allowed origins | `*` |
| `ALLOWED_HOST` | string | Allowed hosts | `*` |
| `ROOT_PATH` | string | API root path | `` |
| `DOCS_PATH` | string | Swagger docs path | `` |
| `REDOCS_PATH` | string | ReDoc path | `` |

### Authentication

| Variable | Type | Description | Required |
|----------|------|-------------|----------|
| `JWT_SECRET_KEY` | string | JWT signing key | Yes (if JWT auth) |
| `JWT_ALGORITHM` | string | JWT algorithm | Yes (if JWT auth) |

### API Keys

| Variable | Type | Description |
|----------|------|-------------|
| `GEMINI_API_KEY` | string | Google Gemini API key |
| `OPENAI_API_KEY` | string | OpenAI API key |
| `ANTHROPIC_API_KEY` | string | Anthropic Claude API key |

### Snowflake ID Generator

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `SNOWFLAKE_EPOCH` | integer | Epoch timestamp (ms) | `1609459200000` |
| `SNOWFLAKE_NODE_ID` | integer | Node ID | `1` |
| `SNOWFLAKE_WORKER_ID` | integer | Worker ID | `2` |
| `SNOWFLAKE_TIME_BITS` | integer | Time bits | `39` |
| `SNOWFLAKE_NODE_BITS` | integer | Node bits | `5` |
| `SNOWFLAKE_WORKER_BITS` | integer | Worker bits | `8` |
| `SNOWFLAKE_TOTAL_BITS` | integer | Total bits | `64` |

### Redis

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `REDIS_URL` | string | Redis connection URL | `null` |

### Sentry

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `SENTRY_DSN` | string | Sentry DSN for error tracking | `null` |

---

## Application Settings

Settings are defined in `agentflow_cli/src/app/core/config/settings.py`.

### Settings Class

```python
from agentflow_cli.src.app.core import get_settings

settings = get_settings()

# Access settings
print(settings.APP_NAME)
print(settings.LOG_LEVEL)
print(settings.REDIS_URL)
```

### Available Settings

```python
class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "MyApp"
    APP_VERSION: str = "0.1.0"
    MODE: str = "development"
    LOG_LEVEL: str = "INFO"
    IS_DEBUG: bool = True
    SUMMARY: str = "Pyagenity Backend"
    
    # CORS
    ORIGINS: str = "*"
    ALLOWED_HOST: str = "*"
    
    # Paths
    ROOT_PATH: str = ""
    DOCS_PATH: str = ""
    REDOCS_PATH: str = ""
    
    # Redis
    REDIS_URL: str | None = None
    
    # Sentry
    SENTRY_DSN: str | None = None
    
    # Snowflake ID Generator
    SNOWFLAKE_EPOCH: int = 1609459200000
    SNOWFLAKE_NODE_ID: int = 1
    SNOWFLAKE_WORKER_ID: int = 2
    SNOWFLAKE_TIME_BITS: int = 39
    SNOWFLAKE_NODE_BITS: int = 5
    SNOWFLAKE_WORKER_BITS: int = 8
```

### Custom Settings

Create a custom settings file:

```python
# app/settings.py
from agentflow_cli.src.app.core.config.settings import Settings

class CustomSettings(Settings):
    # Add your custom settings
    CUSTOM_API_KEY: str = ""
    MAX_UPLOAD_SIZE: int = 10_000_000  # 10 MB
    RATE_LIMIT: int = 100
```

---

## Examples

### Development Configuration

**agentflow.json:**
```json
{
  "agent": "graph.react:app",
  "env": ".env.development",
  "auth": null,
  "checkpointer": null,
  "redis": null,
  "thread_name_generator": null
}
```

**.env.development:**
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# API Keys for testing
GEMINI_API_KEY=your_dev_key

# No Redis in development
REDIS_URL=
```

### Staging Configuration

**agentflow.json:**
```json
{
  "agent": "graph.react:app",
  "env": ".env.staging",
  "auth": "jwt",
  "checkpointer": "storage.checkpointer:redis_checkpointer",
  "redis": "${REDIS_URL}",
  "store": "storage.store:redis_store"
}
```

**.env.staging:**
```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
DEBUG=false

# JWT Auth
JWT_SECRET_KEY=staging-secret-key
JWT_ALGORITHM=HS256

# API Keys
GEMINI_API_KEY=your_staging_key

# Redis
REDIS_URL=redis://staging-redis:6379

# Sentry
SENTRY_DSN=https://xxx@sentry.io/staging-project
```

### Production Configuration

**agentflow.json:**
```json
{
  "agent": "graph.production:production_app",
  "env": ".env.production",
  "auth": {
    "method": "custom",
    "path": "auth.production:ProductionAuth"
  },
  "checkpointer": "storage.checkpointer:redis_checkpointer",
  "injectq": "app.container:production_container",
  "store": "storage.store:postgres_store",
  "redis": "${REDIS_URL}",
  "thread_name_generator": "utils.naming:ProductionNameGenerator"
}
```

**.env.production:**
```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=false

# Application
APP_NAME=AgentFlow Production API
APP_VERSION=1.0.0
SUMMARY=Production Agent API

# CORS (restrict origins)
ORIGINS=https://app.example.com,https://admin.example.com
ALLOWED_HOST=api.example.com

# JWT Auth
JWT_SECRET_KEY=super-secure-production-key
JWT_ALGORITHM=RS256

# API Keys
GEMINI_API_KEY=your_production_key

# Redis with auth
REDIS_URL=redis://user:password@prod-redis:6379/0

# Sentry
SENTRY_DSN=https://xxx@sentry.io/production-project

# Snowflake ID
SNOWFLAKE_EPOCH=1609459200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
```

### Multi-Agent Configuration

**agentflow.json:**
```json
{
  "agent": "agents.orchestrator:main_agent",
  "env": ".env",
  "auth": "jwt",
  "checkpointer": "storage.checkpointer:redis_checkpointer",
  "injectq": "agents.container:agent_container",
  "redis": "${REDIS_URL}"
}
```

**agents/orchestrator.py:**
```python
from agentflow.graph import StateGraph

# Customer Service Agent
customer_service = StateGraph()
# ... configure ...
customer_agent = customer_service.compile()

# Sales Agent
sales_graph = StateGraph()
# ... configure ...
sales_agent = sales_graph.compile()

# Main Orchestrator
main_graph = StateGraph()
# ... configure with sub-agents ...
main_agent = main_graph.compile(checkpointer=redis_checkpointer)
```

### Microservices Configuration

**Service 1 (Auth Service):**
```json
{
  "agent": "services.auth:auth_agent",
  "env": ".env.auth",
  "auth": "jwt",
  "redis": "${REDIS_URL}"
}
```

**Service 2 (Chat Service):**
```json
{
  "agent": "services.chat:chat_agent",
  "env": ".env.chat",
  "auth": "jwt",
  "checkpointer": "storage.checkpointer:redis_checkpointer",
  "redis": "${REDIS_URL}",
  "thread_name_generator": "services.chat.naming:ChatNameGenerator"
}
```

**Service 3 (Analytics Service):**
```json
{
  "agent": "services.analytics:analytics_agent",
  "env": ".env.analytics",
  "auth": null,
  "store": "storage.store:analytics_store",
  "redis": "${REDIS_URL}"
}
```

---

## Configuration Validation

### Validate Configuration

The CLI automatically validates your configuration on startup. Common validation errors:

**Missing Required Fields:**
```
ConfigurationError: 'agent' field is required in agentflow.json
```

**Invalid Module Path:**
```
ConfigurationError: Cannot load module 'graph.react'
```

**JWT Configuration Missing:**
```
ValueError: JWT_SECRET_KEY and JWT_ALGORITHM must be set in environment variables
```

**Invalid Auth Method:**
```
ValueError: Unsupported auth method: invalid_method
```

### Best Practices

1. **Use Environment Variables for Secrets:**
   ```json
   {
     "redis": "${REDIS_URL}"
   }
   ```

2. **Separate Configs per Environment:**
   - `.env.development`
   - `.env.staging`
   - `.env.production`

3. **Version Control:**
   - ✅ Commit: `agentflow.json`
   - ✅ Commit: `.env.example`
   - ❌ Never commit: `.env`, `.env.production`

4. **Document Custom Settings:**
   ```python
   class Settings(BaseSettings):
       CUSTOM_SETTING: str = "default"
       """Description of what this setting does"""
   ```

5. **Validate on Startup:**
   ```python
   settings = get_settings()
   if not settings.GEMINI_API_KEY:
       raise ValueError("GEMINI_API_KEY is required")
   ```

---

## Additional Resources

- [Authentication Guide](./authentication.md)
- [CLI Guide](./cli-guide.md)
- [Deployment Guide](./deployment.md)
- [ID Generation Guide](./id-generation.md)
- [Thread Name Generator Guide](./thread-name-generator.md)
