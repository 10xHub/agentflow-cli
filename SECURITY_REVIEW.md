# Security Review: AgentFlow CLI - Framework & API Generator

**Review Date:** December 31, 2024  
**Reviewed by:** Security Analysis  
**Scope:** Framework security, API generation, and developer configuration guidance  
**Framework Type:** Multi-agent framework and API generator (similar to LangGraph, ADK)

---

## Executive Summary

This security review covers the AgentFlow CLI project from the perspective of a **framework and API generator** rather than an end-user application. AgentFlow is designed to help developers deploy their agent code as production APIs, similar to LangGraph or other agent deployment frameworks.

The review distinguishes between:
1. **Framework-level security issues** - vulnerabilities in the framework itself
2. **Developer configuration responsibilities** - security decisions intentionally left to developers
3. **Security guidance** - best practices for developers using the framework

**Key Finding:** The framework is generally well-architected for its purpose. Most identified "issues" are actually intentional design decisions that give developers flexibility, which is appropriate for a framework.

---

## Table of Contents

1. [Framework Architecture & Security Model](#1-framework-architecture--security-model)
2. [Actual Framework Security Issues](#2-actual-framework-security-issues)
3. [Developer Configuration Responsibilities](#3-developer-configuration-responsibilities)
4. [Security Guidance for Developers](#4-security-guidance-for-developers)
5. [Comparison with LangGraph/ADK](#5-comparison-with-langgraphadk)
6. [Framework Security Checklist](#6-framework-security-checklist)

---

## 1. Framework Architecture & Security Model

### 1.1 Framework Purpose

AgentFlow CLI is a **framework and deployment tool** that:
- Loads user-defined agent code dynamically (by design)
- Generates FastAPI-based REST APIs from agent definitions
- Provides CLI tools for Docker containerization
- Offers pluggable authentication backends
- Allows developers to configure CORS, rate limiting, and other security policies

### 1.2 Security Responsibilities

| Component | Responsibility | Notes |
|-----------|---------------|-------|
| **Authentication Backend** | Developer | Pluggable - JWT, custom, or none |
| **CORS Configuration** | Developer | Environment-specific |
| **Authorization Logic** | Developer | App-specific business rules |
| **Rate Limiting** | Developer | Traffic patterns vary by use case |
| **Input Validation** | Shared | Framework + developer schemas |
| **Code Loading** | By Design | Must load user agent code |
| **Error Messages** | Shared | Framework provides hooks |

### 1.3 Threat Model

**In Scope:**
- Framework code vulnerabilities
- Insecure defaults that could harm developers
- Missing security hooks/extension points
- Information leakage from framework code

**Out of Scope:**
- Developer's agent logic security
- Developer's authentication implementation
- Developer's production configuration
- Third-party dependencies chosen by developers

---

## 2. Actual Framework Security Issues

These are vulnerabilities in the framework itself that should be fixed.

### 2.1 Missing Authorization Middleware/Hooks (HIGH)

**Location:** API routers (`graph/router.py`, `checkpointer/router.py`, `store/router.py`)

**Issue:** The framework provides authentication but lacks built-in resource-level authorization patterns or hooks.

```python
# Current: Only authentication check
async def get_state(
    thread_id: int | str,
    user: dict[str, Any] = Depends(verify_current_user),
):
    config = {"thread_id": thread_id}
    result = await service.get_state(config, user)
```

**Why This Is a Framework Issue:**
Unlike application-level authorization (which is developer responsibility), the framework should provide patterns or hooks for developers to implement authorization. Currently, there's no clear extension point.

**How LangGraph Handles This:**
LangGraph Studio uses a middleware pattern where developers can inject authorization logic:
```python
# LangGraph pattern
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Developer implements their auth logic here
    user = await get_user(request)
    request.state.user = user
    return await call_next(request)
```

**Recommendation:**
Add authorization middleware hooks:

```python
# New authorization hook system
class AuthorizationHook:
    async def can_access_thread(
        self, user: dict, thread_id: str, action: str
    ) -> bool:
        """Override this in your auth backend."""
        return True  # Default allows all

# In auth_backend.py
def verify_current_user(...) -> dict[str, Any]:
    # ... existing code ...
    
    # Add authorization hook to request state
    request.state.authorize = auth_backend.authorize if auth_backend else None
    return user

# Usage in endpoints
async def get_state(...):
    if request.state.authorize:
        allowed = await request.state.authorize("thread", thread_id, "read", user)
        if not allowed:
            raise HTTPException(403, "Access denied")
    
    result = await service.get_state(config, user)
```

### 2.2 User Context Not Properly Injected in Service Layer (MEDIUM)

**Location:** `checkpointer_service.py`, `store_service.py`

**Issue:** User context is manually merged into config in each service method rather than being automatically available.

```python
def _config(self, config: dict[str, Any] | None, user: dict) -> dict[str, Any]:
    cfg: dict[str, Any] = dict(config or {})
    cfg["user"] = user
    cfg["user_id"] = user.get("user_id", "anonymous")
    return cfg
```

**Problem:** This pattern is error-prone and could lead to user context being missed.

**Recommendation:**
Use dependency injection to automatically attach user context:

```python
# In InjectQ configuration
def configure_user_context(container: InjectQ):
    # Automatically inject current user into all service calls
    container.bind_scoped(UserContext, lambda: get_current_user_from_context())

# Services receive it automatically
@singleton
class CheckpointerService:
    @inject
    def __init__(
        self,
        checkpointer: BaseCheckpointer,
        user_context: UserContext = Inject[UserContext]
    ):
        self.checkpointer = checkpointer
        self.user_context = user_context
```

### 2.3 Sensitive Data in Debug Logs (MEDIUM)

**Location:** Multiple files

**Issue:** Framework logs user dictionaries at DEBUG level without sanitization.

```python
logger.debug(f"User info: {user}")
```

**Why This Is a Framework Issue:**
The framework should not log potentially sensitive user data by default, even at DEBUG level.

**Recommendation:**

```python
# Add to logger.py
def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from logging output."""
    SENSITIVE_PATTERNS = {'token', 'password', 'secret', 'key', 'credential', 'authorization'}
    
    if not isinstance(data, dict):
        return data
    
    return {
        k: '***REDACTED***' if any(p in k.lower() for p in SENSITIVE_PATTERNS) else v
        for k, v in data.items()
    }

# Update usage
logger.debug(f"User context: {sanitize_for_logging(user)}")
```

### 2.4 No Framework-Level Request Size Limits (MEDIUM)

**Location:** FastAPI app configuration

**Issue:** Framework doesn't set any default request size limits.

**Recommendation:**

```python
# In main.py
app = FastAPI(
    ...
    # Add reasonable framework defaults
    # Developers can override in their config
)

# Add middleware for request size limiting
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_size:
                return JSONResponse(
                    {"error": "Request too large"},
                    status_code=413
                )
        return await call_next(request)
```

### 2.5 Error Messages Could Expose Framework Internals (LOW)

**Location:** `handle_errors.py`

**Issue:** Error handlers might expose internal framework structure.

**Recommendation:**

```python
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    settings = get_settings()
    
    # Always log full error server-side with correlation ID
    correlation_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(
        f"Unhandled exception [correlation_id={correlation_id}]",
        exc_info=exc,
        extra={"correlation_id": correlation_id}
    )
    
    # Return safe message to client
    if settings.IS_DEBUG:
        message = str(exc)  # Full error in development
    else:
        message = "An internal error occurred. Please contact support with correlation ID: " + correlation_id
    
    return error_response(
        request,
        error_code="INTERNAL_ERROR",
        message=message,
        status_code=500,
    )
```

---

## 3. Developer Configuration Responsibilities

These are intentional design decisions where developers must configure security for their use case.

### 3.1 Authentication Backend Configuration (Developer Choice)

**Location:** `agentflow.json`, `auth_backend.py`

**Framework Behavior:** ✅ Working as designed

```python
# Framework provides pluggable auth
def verify_current_user(...) -> dict[str, Any]:
    backend = config.auth_config()
    if not backend:
        return {}  # No auth configured - developer's choice
```

**Developer Responsibility:**
- Choose authentication method (JWT, custom, OAuth, etc.)
- Configure JWT secrets and algorithms
- Implement custom auth backend if needed
- Decide if endpoints require authentication

**Framework Documentation Should State:**
```markdown
## Authentication Configuration

AgentFlow provides pluggable authentication. You must configure authentication
for production deployments:

### Option 1: JWT Authentication
```json
{
  "auth": "jwt"
}
```

Set environment variables:
- `JWT_SECRET_KEY`: Minimum 32 characters, use cryptographically secure random string
- `JWT_ALGORITHM`: Use HS256, HS384, or HS512

### Option 2: Custom Authentication
```json
{
  "auth": {
    "method": "custom",
    "path": "myapp.auth:custom_auth_backend"
  }
}
```

### Option 3: No Authentication (Development Only)
```json
{
  "auth": null
}
```
⚠️ **Warning:** Only use for local development. Never deploy to production without authentication.
```

### 3.2 CORS Configuration (Developer Choice)

**Location:** `settings.py`

**Framework Behavior:** ✅ Working as designed

```python
ORIGINS: str = "*"  # Default for development ease
ALLOWED_HOST: str = "*"
```

**Developer Responsibility:**
Configure CORS for their environment via environment variables:

```bash
# Development
ORIGINS=*
ALLOWED_HOST=*

# Production
ORIGINS=https://myapp.com,https://www.myapp.com
ALLOWED_HOST=myapp.com,www.myapp.com
```

**Framework Improvement:**
Add validation warning:

```python
@validator("ORIGINS", "ALLOWED_HOST")
def warn_wildcard_cors(cls, v, field):
    if v == "*" and os.environ.get("MODE", "").lower() == "production":
        logger.warning(
            f"⚠️  {field.name}='*' in production mode. "
            f"This allows any origin to access your API. "
            f"Set {field.name} to specific domains for production."
        )
    return v
```

### 3.3 Rate Limiting (Developer Choice)

**Location:** Not implemented (by design)

**Rationale:** Rate limiting needs vary drastically:
- Development: No limits
- Internal APIs: High limits
- Public APIs: Strict limits per user/IP
- Enterprise: Different tiers

**Developer Responsibility:**
Add rate limiting middleware:

```python
# Developer's code
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/v1/graph/invoke")
@limiter.limit("100/minute")
async def invoke_graph(...):
    ...
```

**Framework Improvement:**
Provide optional rate limiting helper:

```python
# In agentflow_cli/src/app/utils/rate_limit.py
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

def setup_rate_limiting(
    app: FastAPI,
    default_limits: Optional[str] = None,
    storage_uri: Optional[str] = None
):
    """
    Optional rate limiting setup helper.
    
    Args:
        app: FastAPI app
        default_limits: e.g., "100/minute"
        storage_uri: Redis URI for distributed rate limiting
    
    Example:
        from agentflow_cli.src.app.utils.rate_limit import setup_rate_limiting
        setup_rate_limiting(app, default_limits="100/minute")
    """
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[default_limits] if default_limits else [],
        storage_uri=storage_uri
    )
    app.state.limiter = limiter
    return limiter
```

### 3.4 Dynamic Code Loading (By Design - Required Feature)

**Location:** `loader.py`

**Framework Behavior:** ✅ Working as designed

```python
async def load_graph(path: str) -> CompiledGraph | None:
    module_name_importable, function_name = path.split(":")
    module = importlib.import_module(module_name_importable)
    entry_point_obj = getattr(module, function_name)
```

**Why This Is Required:**
The framework **must** load user-defined agent code. This is equivalent to:
- Django loading `settings.py`
- Flask loading application factory
- LangGraph loading graph definitions

**Developer Responsibility:**
- Only specify trusted module paths in `agentflow.json`
- Ensure their agent code is secure
- Review dependencies

**Not a Security Issue Because:**
The `agentflow.json` file is created and controlled by the developer. If an attacker can modify this file, they already have code execution capability.

**Framework Improvement:**
Add validation that the path follows expected patterns:

```python
def validate_module_path(path: str) -> tuple[str, str]:
    """Validate module path follows expected pattern."""
    if ":" not in path:
        raise ValueError(
            "Path must be in format 'module.path:function_name'\n"
            "Example: 'graph.react:app'"
        )
    
    module_name, function_name = path.rsplit(":", 1)
    
    # Warn about unusual patterns
    if ".." in module_name or module_name.startswith("/"):
        logger.warning(
            f"Unusual module path detected: {module_name}. "
            f"Ensure this is intentional."
        )
    
    return module_name, function_name
```

### 3.5 Input Validation (Shared Responsibility)

**Framework Provides:**
- Pydantic schemas for API inputs
- Basic type validation
- Request/response models

**Developer Adds:**
- Domain-specific validation
- Size limits for their use case
- Custom validators

**Example:**

```python
# Developer extends framework schemas
from agentflow_cli.src.app.routers.graph.schemas import GraphInputSchema
from pydantic import validator, Field

class MyGraphInputSchema(GraphInputSchema):
    messages: list[Message] = Field(..., max_items=50)
    
    @validator('messages')
    def validate_content_size(cls, messages):
        for msg in messages:
            if len(msg.content) > 10000:
                raise ValueError("Message content too large")
        return messages
```

---

## 4. Security Guidance for Developers

### 4.1 Production Deployment Checklist

When deploying AgentFlow-based APIs to production:

- [ ] **Configure authentication**
  - [ ] Set strong `JWT_SECRET_KEY` (minimum 32 characters, cryptographically random)
  - [ ] Use secure JWT algorithm (HS256 or better)
  - [ ] Or implement custom auth backend
  
- [ ] **Set CORS policies**
  - [ ] Set `ORIGINS` to specific domains
  - [ ] Set `ALLOWED_HOST` to your domains
  - [ ] Never use `*` in production

- [ ] **Configure environment**
  - [ ] Set `MODE=production`
  - [ ] Set `IS_DEBUG=false`
  - [ ] Disable docs: `DOCS_PATH=null`, `REDOCS_PATH=null`

- [ ] **Add rate limiting**
  - [ ] Install and configure rate limiter
  - [ ] Set appropriate limits for your use case

- [ ] **Implement authorization**
  - [ ] Add resource ownership checks
  - [ ] Implement role-based access control if needed
  - [ ] Use authorization hooks provided by framework

- [ ] **Enable security headers**
  - [ ] Add HTTPS enforcement
  - [ ] Configure security headers middleware
  - [ ] Enable HSTS

- [ ] **Set up monitoring**
  - [ ] Configure Sentry (already integrated)
  - [ ] Set up log aggregation
  - [ ] Monitor for security events

### 4.2 Secure Configuration Example

```python
# Production .env
MODE=production
IS_DEBUG=false

# Authentication
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
JWT_ALGORITHM=HS256

# CORS
ORIGINS=https://myapp.com,https://www.myapp.com
ALLOWED_HOST=myapp.com,www.myapp.com

# Docs (disable in production)
DOCS_PATH=
REDOCS_PATH=

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=INFO
```

```json
// agentflow.json
{
  "agent": "myagent.graph:app",
  "env": ".env.production",
  "auth": "jwt",
  "checkpointer": "myagent.checkpointer:checkpointer",
  "store": "myagent.store:store"
}
```

### 4.3 Authorization Implementation Pattern

```python
# myagent/auth.py
from agentflow_cli.src.app.core.auth import BaseAuth

class MyAuthBackend(BaseAuth):
    def authenticate(self, request, response, credential):
        # Your JWT validation
        user = decode_jwt(credential.credentials)
        return user
    
    async def authorize(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        user: dict
    ) -> bool:
        """Check if user can perform action on resource."""
        if action == "read":
            return await self.can_read(user, resource_type, resource_id)
        elif action == "write":
            return await self.can_write(user, resource_type, resource_id)
        elif action == "delete":
            return await self.can_delete(user, resource_type, resource_id)
        return False
    
    async def can_read(self, user, resource_type, resource_id):
        # Your business logic
        if resource_type == "thread":
            thread = await get_thread(resource_id)
            return thread.user_id == user["user_id"]
        return False
```

---

## 5. Comparison with LangGraph/ADK

### 5.1 LangGraph Studio Approach

LangGraph Studio (their deployment platform) takes a similar approach:

**Authentication:**
- Pluggable auth backends
- Developer implements authentication
- No auth required for local development
- Supports API keys, OAuth, custom auth

**Authorization:**
- Middleware-based approach
- Developer hooks for authorization checks
- No built-in RBAC (developer's responsibility)

**Code Loading:**
- Loads user graph definitions from config
- Similar to AgentFlow's approach
- No validation on module paths (developer controls config)

**CORS:**
- Configurable via environment
- Defaults to permissive for development
- Developer sets production values

### 5.2 ADK (Agent Development Kit) Approach

Microsoft's ADK takes similar design decisions:

**Security Model:**
- Framework provides infrastructure
- Developer implements security policies
- Pluggable components for auth/authz
- Environment-based configuration

### 5.3 Key Takeaway

Industry-standard agent frameworks:
- **Do NOT** enforce specific auth/authz mechanisms
- **Do** provide hooks and extension points
- **Do** trust developers to secure their applications
- **Do NOT** restrict code loading (it's a core feature)

---

## 6. Framework Security Checklist

### 6.1 Framework-Level (AgentFlow's Responsibility)

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| Authorization middleware hooks | ⚠️ Needs improvement | HIGH | Add extension points for custom authz |
| Sensitive data sanitization in logs | ❌ Missing | MEDIUM | Framework shouldn't log sensitive fields |
| Request size limits | ❌ Missing | MEDIUM | Add framework defaults |
| Error message sanitization | ⚠️ Partial | MEDIUM | Better prod/dev separation |
| Security header helpers | ❌ Missing | LOW | Provide optional middleware |
| Rate limiting helpers | ❌ Missing | LOW | Provide optional utilities |
| Documentation on secure deployment | ⚠️ Basic | HIGH | Comprehensive security guide needed |

### 6.2 Developer-Level (User's Responsibility)

| Item | Developer Action | Notes |
|------|------------------|-------|
| JWT configuration | Set strong secret, validate algorithm | Required for production |
| CORS policy | Configure specific origins | Never use `*` in production |
| Authentication backend | Choose and configure auth method | JWT, OAuth, custom |
| Authorization logic | Implement resource ownership checks | Business logic specific |
| Rate limiting | Add rate limiter to app | Use slowapi or similar |
| Input validation | Extend schemas with domain rules | Framework provides base |
| Production config | Set MODE, disable debug/docs | Critical for security |
| HTTPS deployment | Configure reverse proxy | Nginx, Traefik, etc. |
| Secrets management | Use Vault, AWS Secrets, etc. | Never hardcode secrets |
| Monitoring | Set up Sentry, logs, alerts | Framework supports Sentry |

---

## 7. Recommended Framework Improvements

### Priority 1: Add Authorization Hooks

```python
# agentflow_cli/src/app/core/auth/authorization.py
from abc import ABC, abstractmethod
from typing import Any

class AuthorizationBackend(ABC):
    """Base class for authorization backends."""
    
    @abstractmethod
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context
    ) -> bool:
        """
        Check if user can perform action on resource.
        
        Args:
            user: Authenticated user dict
            resource: Resource type (thread, message, memory)
            action: Action to perform (read, write, delete)
            resource_id: Optional specific resource ID
            context: Additional context for decision
            
        Returns:
            True if authorized, False otherwise
        """
        pass

class DefaultAuthorizationBackend(AuthorizationBackend):
    """Default authorization - allows all authenticated users."""
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        # If user is authenticated, allow everything
        return bool(user.get("user_id"))

# Usage in endpoint
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend

async def get_state(
    thread_id: str,
    user: dict = Depends(verify_current_user),
    authz: AuthorizationBackend = InjectAPI(AuthorizationBackend),
):
    # Authorization check
    if not await authz.authorize(user, "thread", "read", thread_id):
        raise HTTPException(403, "Access denied")
    
    result = await service.get_state({"thread_id": thread_id}, user)
    return success_response(result, request)
```

**Developer implements custom authz:**

```python
# myapp/auth.py
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend

class MyAuthorizationBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        if resource == "thread":
            return await self.check_thread_access(user, resource_id, action)
        elif resource == "memory":
            return await self.check_memory_access(user, resource_id, action)
        return False
    
    async def check_thread_access(self, user, thread_id, action):
        # Your business logic
        thread = await get_thread(thread_id)
        if action == "read":
            return thread.user_id == user["user_id"] or user.get("is_admin")
        elif action == "write":
            return thread.user_id == user["user_id"]
        return False
```

### Priority 2: Add Security Configuration Warnings

```python
# agentflow_cli/src/app/core/config/settings.py
from pydantic import validator
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # ... existing fields ...
    
    @validator("ORIGINS")
    def warn_cors_wildcard(cls, v):
        """Warn about CORS wildcard in production."""
        mode = os.environ.get("MODE", "development").lower()
        if v == "*" and mode == "production":
            logger.warning(
                "⚠️  SECURITY WARNING: CORS ORIGINS set to '*' in production mode.\n"
                "   This allows any website to make requests to your API.\n"
                "   Set ORIGINS to specific domains: ORIGINS=https://myapp.com,https://www.myapp.com"
            )
        return v
    
    @validator("MODE", pre=True)
    def normalize_mode(cls, v):
        """Normalize mode to lowercase."""
        return v.lower() if v else "development"
    
    def model_post_init(self, __context):
        """Post-init validation and warnings."""
        if self.MODE == "production":
            if self.IS_DEBUG:
                logger.warning("⚠️  DEBUG mode enabled in production!")
            if self.DOCS_PATH or self.REDOCS_PATH:
                logger.warning("⚠️  API documentation endpoints enabled in production!")
```

### Priority 3: Add Log Sanitization

```python
# agentflow_cli/src/app/core/logger.py
from typing import Any
import re

SENSITIVE_PATTERNS = {
    'token', 'password', 'secret', 'key', 'credential', 
    'authorization', 'api_key', 'access_token', 'refresh_token'
}

def sanitize_for_logging(data: Any) -> Any:
    """Recursively sanitize sensitive data for logging."""
    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if any(p in k.lower() for p in SENSITIVE_PATTERNS) else sanitize_for_logging(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        # Redact JWT tokens
        if re.match(r'^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$', data):
            return '***JWT_TOKEN***'
        return data
    return data

# Update all logger.debug calls:
logger.debug(f"User context: {sanitize_for_logging(user)}")
```

### Priority 4: Add Request Size Middleware

```python
# agentflow_cli/src/app/core/config/request_limits.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent memory exhaustion."""
    
    def __init__(
        self,
        app,
        max_size: int = 10 * 1024 * 1024  # 10MB default
    ):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request, call_next):
        if "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_size:
                return JSONResponse(
                    {
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request body too large. Maximum size: {self.max_size} bytes"
                        }
                    },
                    status_code=413
                )
        return await call_next(request)

# Add to setup_middleware
app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)
```

---

## 8. Security Documentation for Developers

The framework should include comprehensive security documentation:

### 8.1 README Section

```markdown
## Security Considerations

AgentFlow is a framework for deploying agent applications. **You are responsible for securing your deployment.**

### Production Deployment Checklist

Before deploying to production:

1. **Authentication** - Configure your auth backend
2. **Authorization** - Implement resource ownership checks
3. **CORS** - Set specific allowed origins (never use `*`)
4. **Environment** - Set MODE=production, disable debug
5. **Secrets** - Use strong, random secrets (32+ characters)
6. **HTTPS** - Deploy behind HTTPS reverse proxy
7. **Rate Limiting** - Add rate limiting for public endpoints
8. **Monitoring** - Configure Sentry and log aggregation

See [SECURITY.md](SECURITY.md) for detailed guidance.
```

### 8.2 SECURITY.md File

Create a comprehensive security guide for developers covering:
- Threat model
- Authentication setup
- Authorization patterns
- Secure configuration examples
- Docker deployment security
- Secrets management
- Incident response
- Security updates

---

## 9. Conclusion

### 9.1 Framework Security Status

**Current State:**
- ✅ Pluggable authentication system
- ✅ Environment-based configuration
- ✅ Error handling infrastructure
- ⚠️ Missing authorization hooks
- ⚠️ Logs sensitive data
- ⚠️ Lacks security warnings

**Recommended Actions:**

**Immediate (1-2 weeks):**
1. Add authorization backend interface and hooks
2. Implement log sanitization
3. Add security configuration warnings
4. Create comprehensive security documentation

**Short-term (1-2 months):**
1. Add request size limit middleware
2. Provide rate limiting helpers
3. Add security header middleware
4. Create security examples in docs

**Long-term:**
1. Add security best practices guide
2. Create secure deployment templates
3. Provide audit logging helpers
4. Develop security testing tools

### 9.2 Developer Responsibility Summary

When using AgentFlow, developers must:
- ✅ Configure authentication for production
- ✅ Implement authorization logic
- ✅ Set secure CORS policies
- ✅ Use strong secrets
- ✅ Deploy behind HTTPS
- ✅ Add rate limiting
- ✅ Monitor and maintain their deployment

### 9.3 Final Assessment

**AgentFlow is appropriately designed as a framework.** Most "security issues" identified are actually:
1. Intentional design decisions giving developers flexibility
2. Configuration responsibilities left to developers
3. Features that require developer implementation

The framework should focus on:
- Providing better hooks and extension points
- Adding helpful warnings and validation
- Documenting security best practices
- Creating secure-by-default helpers

**Framework Security Grade: B+**
- Strong foundation
- Needs better authorization patterns
- Requires improved documentation
- Should add developer warnings

---

*This security review acknowledges AgentFlow's role as a framework. Actual security depends heavily on how developers configure and deploy their applications.*
