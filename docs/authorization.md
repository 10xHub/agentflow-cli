# Authorization Guide

## Overview

AgentFlow CLI provides a flexible, pluggable authorization system that allows you to implement resource-level access control for your multi-agent applications. Authorization determines **what authenticated users can do**, complementing the authentication system which determines **who users are**.

## Key Concepts

### Authorization vs Authentication

- **Authentication** (covered in [authentication.md](authentication.md)): Verifies user identity and returns user information
- **Authorization**: Determines if an authenticated user has permission to perform specific actions on resources

### Authorization Backend

The authorization backend is a pluggable component that implements the `AuthorizationBackend` abstract class. It receives:
- **User context**: Information about the authenticated user
- **Resource**: The type of resource being accessed (e.g., "graph", "checkpointer", "store")
- **Action**: The operation being performed (e.g., "invoke", "read", "write", "delete")
- **Resource ID**: Optional specific identifier (e.g., thread_id, memory_id)
- **Additional context**: Extra information for authorization decisions

The backend returns `True` if authorized, `False` otherwise. On `False`, the API returns a 403 Forbidden response.

## Default Behavior

If you don't configure a custom authorization backend, AgentFlow uses `DefaultAuthorizationBackend`, which:
- Allows all authenticated users to perform any action
- Only checks that the user has a `user_id` (i.e., they're authenticated)
- Suitable for development and simple use cases

## Implementing Custom Authorization

### Step 1: Create Your Authorization Backend

Create a Python file (e.g., `my_auth/authorization.py`) and implement the `AuthorizationBackend` class:

```python
from typing import Any
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend

class RoleBasedAuthorizationBackend(AuthorizationBackend):
    """
    Example: Role-based access control (RBAC)
    
    Users have roles (admin, user, viewer) with different permissions.
    """
    
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context: Any,
    ) -> bool:
        """
        Check if user can perform action on resource.
        
        Args:
            user: User info dict (from authentication)
            resource: "graph", "checkpointer", or "store"
            action: "invoke", "stream", "read", "write", "delete", etc.
            resource_id: Optional specific resource identifier
            **context: Additional context (e.g., request payload)
            
        Returns:
            bool: True if authorized, False otherwise
        """
        # Extract user role from user info
        user_role = user.get("role", "viewer")
        user_id = user.get("user_id")
        
        # Admins can do anything
        if user_role == "admin":
            return True
        
        # Graph operations
        if resource == "graph":
            if action in ["invoke", "stream"]:
                # Users and viewers can invoke/stream
                return user_role in ["user", "viewer"]
            elif action in ["stop", "setup", "fix"]:
                # Only users and admins can modify
                return user_role == "user"
        
        # Checkpointer operations
        elif resource == "checkpointer":
            if action == "read":
                # Everyone can read their own data
                return True
            elif action in ["write", "delete"]:
                # Only users and admins can modify
                return user_role == "user"
        
        # Store operations
        elif resource == "store":
            if action == "read":
                # Everyone can read
                return True
            elif action in ["write", "delete"]:
                # Only users and admins can modify
                return user_role == "user"
        
        # Deny by default
        return False


# Create an instance to export
authorization_backend = RoleBasedAuthorizationBackend()
```

### Step 2: Configure in agentflow.json

Add the authorization configuration to your `agentflow.json`:

```json
{
  "agent": "my_agent.graph:agent",
  "checkpointer": "my_agent.checkpointer:checkpointer",
  "store": "my_agent.store:store",
  "auth": {
    "method": "jwt",
    "path": "my_auth.auth_backend:auth_backend"
  },
  "authorization": "my_auth.authorization:authorization_backend"
}
```

The `authorization` field should point to your authorization backend instance in the format:
```
"module.path:attribute_name"
```

### Step 3: Test Your Authorization

Start your API and test with different user roles:

```bash
# Admin user can do anything
curl -X POST http://localhost:8000/v1/graph/invoke \
  -H "Authorization: Bearer <admin-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'

# Viewer can invoke but cannot stop
curl -X POST http://localhost:8000/v1/graph/stop \
  -H "Authorization: Bearer <viewer-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "123"}'
# Returns: 403 Forbidden
```

## Common Authorization Patterns

### 1. Role-Based Access Control (RBAC)

Users have roles (admin, user, viewer) with predefined permissions:

```python
class RBACBackend(AuthorizationBackend):
    PERMISSIONS = {
        "admin": ["*"],  # All actions
        "user": ["invoke", "stream", "read", "write"],
        "viewer": ["read"]
    }
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        role = user.get("role", "viewer")
        allowed_actions = self.PERMISSIONS.get(role, [])
        return "*" in allowed_actions or action in allowed_actions

authorization_backend = RBACBackend()
```

### 2. Attribute-Based Access Control (ABAC)

Fine-grained control based on user attributes, resource attributes, and context:

```python
class ABACBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        user_id = user.get("user_id")
        user_department = user.get("department")
        
        # Users can only access their own threads
        if resource == "checkpointer" and resource_id:
            thread_owner = await self.get_thread_owner(resource_id)
            if thread_owner != user_id:
                return False
        
        # Department-specific access
        if user_department == "engineering":
            return True
        elif user_department == "sales":
            # Sales can only invoke, not modify
            return action in ["invoke", "stream", "read"]
        
        return False
    
    async def get_thread_owner(self, thread_id):
        # Query your database to get thread owner
        # This is just an example
        return "some-user-id"

authorization_backend = ABACBackend()
```

### 3. Owner-Based Access Control

Users can only access resources they created:

```python
class OwnershipBackend(AuthorizationBackend):
    def __init__(self, checkpointer):
        self.checkpointer = checkpointer
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        user_id = user.get("user_id")
        
        # For checkpointer operations, verify thread ownership
        if resource == "checkpointer" and resource_id:
            state = await self.checkpointer.aget_state({"thread_id": resource_id})
            if state and state.config.get("user_id") != user_id:
                return False
        
        # For store operations, verify memory ownership
        if resource == "store" and resource_id:
            memory = await self.get_memory(resource_id)
            if memory and memory.get("user_id") != user_id:
                return False
        
        # Allow if no specific resource or if owner matches
        return True
    
    async def get_memory(self, memory_id):
        # Retrieve memory and check ownership
        return {"user_id": "owner-id"}

# You'll need to pass checkpointer instance
# This requires modifying loader.py to support constructor args
authorization_backend = OwnershipBackend(checkpointer=None)
```

### 4. API Key Tier-Based Access

Different access levels based on API key tiers:

```python
class TierBasedBackend(AuthorizationBackend):
    TIER_LIMITS = {
        "free": {"max_requests_per_day": 100, "allowed_actions": ["invoke", "read"]},
        "pro": {"max_requests_per_day": 10000, "allowed_actions": ["invoke", "stream", "read", "write"]},
        "enterprise": {"max_requests_per_day": -1, "allowed_actions": ["*"]}
    }
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        tier = user.get("tier", "free")
        tier_config = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["free"])
        
        # Check if action is allowed for this tier
        allowed_actions = tier_config["allowed_actions"]
        if "*" not in allowed_actions and action not in allowed_actions:
            return False
        
        # Check rate limits (simplified)
        # In production, use Redis or similar for rate limiting
        request_count = await self.get_request_count(user["user_id"])
        max_requests = tier_config["max_requests_per_day"]
        if max_requests > 0 and request_count >= max_requests:
            return False
        
        return True
    
    async def get_request_count(self, user_id):
        # Check request count from cache/database
        return 50  # Example

authorization_backend = TierBasedBackend()
```

## Authorization Check Points

Authorization is checked at the following points in the API:

### Graph Endpoints

| Endpoint | Resource | Action | Resource ID |
|----------|----------|--------|-------------|
| `POST /v1/graph/invoke` | `graph` | `invoke` | `thread_id` (if provided) |
| `POST /v1/graph/stream` | `graph` | `stream` | `thread_id` (if provided) |
| `GET /v1/graph` | `graph` | `read` | None |
| `GET /v1/graph:StateSchema` | `graph` | `read` | None |
| `POST /v1/graph/stop` | `graph` | `stop` | `thread_id` |
| `POST /v1/graph/setup` | `graph` | `setup` | None |
| `POST /v1/graph/fix` | `graph` | `fix` | `thread_id` |

### Checkpointer Endpoints

| Endpoint | Resource | Action | Resource ID |
|----------|----------|--------|-------------|
| `GET /v1/threads/{thread_id}/state` | `checkpointer` | `read` | `thread_id` |
| `PUT /v1/threads/{thread_id}/state` | `checkpointer` | `write` | `thread_id` |
| `DELETE /v1/threads/{thread_id}/state` | `checkpointer` | `delete` | `thread_id` |
| `POST /v1/threads/{thread_id}/messages` | `checkpointer` | `write` | `thread_id` |
| `GET /v1/threads/{thread_id}/messages/{message_id}` | `checkpointer` | `read` | `thread_id` |
| `GET /v1/threads/{thread_id}/messages` | `checkpointer` | `read` | `thread_id` |
| `DELETE /v1/threads/{thread_id}/messages/{message_id}` | `checkpointer` | `delete` | `thread_id` |
| `GET /v1/threads/{thread_id}` | `checkpointer` | `read` | `thread_id` |
| `GET /v1/threads` | `checkpointer` | `read` | None |
| `DELETE /v1/threads/{thread_id}` | `checkpointer` | `delete` | `thread_id` |

### Store Endpoints

| Endpoint | Resource | Action | Resource ID |
|----------|----------|--------|-------------|
| `POST /v1/store/memories` | `store` | `write` | `namespace` (if provided) |
| `POST /v1/store/search` | `store` | `read` | `namespace` (if provided) |
| `POST /v1/store/memories/{memory_id}` | `store` | `read` | `memory_id` |
| `POST /v1/store/memories/list` | `store` | `read` | None |
| `PUT /v1/store/memories/{memory_id}` | `store` | `write` | `memory_id` |
| `DELETE /v1/store/memories/{memory_id}` | `store` | `delete` | `memory_id` |
| `POST /v1/store/memories/forget` | `store` | `delete` | `namespace` (if provided) |

## Best Practices

### 1. Start Simple, Scale Up

Begin with the `DefaultAuthorizationBackend` and add complexity as needed:

```python
# Stage 1: Default (all authenticated users)
# No configuration needed - this is the default

# Stage 2: Simple role check
class SimpleRoleBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        return user.get("role") in ["admin", "user"]

# Stage 3: Resource-specific logic
# Add conditions based on resource type

# Stage 4: Fine-grained ABAC
# Consider attributes, context, time, location, etc.
```

### 2. Fail Secure (Deny by Default)

Always return `False` at the end of your authorization logic:

```python
async def authorize(self, user, resource, action, resource_id=None, **context):
    # Check various conditions
    if condition1:
        return True
    if condition2:
        return True
    
    # Deny everything else
    return False
```

### 3. Log Authorization Failures

Add logging to help debug authorization issues:

```python
import logging

logger = logging.getLogger(__name__)

class MyAuthBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        user_id = user.get("user_id")
        
        if not self.has_permission(user, resource, action):
            logger.warning(
                f"Authorization denied: user={user_id}, resource={resource}, "
                f"action={action}, resource_id={resource_id}"
            )
            return False
        
        logger.info(f"Authorization granted: user={user_id}, action={action}")
        return True
```

### 4. Cache Authorization Decisions

For expensive authorization checks (e.g., database queries), implement caching:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedAuthBackend(AuthorizationBackend):
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        # Create cache key
        cache_key = f"{user['user_id']}:{resource}:{action}:{resource_id}"
        
        # Check cache
        if cache_key in self.cache:
            cached_value, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_value
        
        # Compute authorization
        result = await self._compute_authorization(user, resource, action, resource_id)
        
        # Cache result
        self.cache[cache_key] = (result, datetime.now())
        
        return result
    
    async def _compute_authorization(self, user, resource, action, resource_id):
        # Your actual authorization logic here
        return True

authorization_backend = CachedAuthBackend()
```

### 5. Separate Concerns

Keep authorization logic separate from business logic:

```python
# ✅ Good: Authorization in backend
class MyAuthBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        return user.get("role") == "admin"

# ❌ Bad: Don't add authorization to your graph/service code
# The framework handles this automatically
```

### 6. Use Type Hints

Make your code maintainable with proper type hints:

```python
from typing import Any, Optional

class TypedAuthBackend(AuthorizationBackend):
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        **context: Any,
    ) -> bool:
        # Implementation
        return True
```

## Testing Authorization

### Unit Testing

```python
import pytest
from my_auth.authorization import RoleBasedAuthorizationBackend

@pytest.fixture
def auth_backend():
    return RoleBasedAuthorizationBackend()

@pytest.mark.asyncio
async def test_admin_can_do_anything(auth_backend):
    user = {"user_id": "admin-1", "role": "admin"}
    assert await auth_backend.authorize(user, "graph", "invoke") == True
    assert await auth_backend.authorize(user, "checkpointer", "delete", "thread-1") == True

@pytest.mark.asyncio
async def test_viewer_cannot_write(auth_backend):
    user = {"user_id": "viewer-1", "role": "viewer"}
    assert await auth_backend.authorize(user, "graph", "read") == True
    assert await auth_backend.authorize(user, "checkpointer", "write", "thread-1") == False

@pytest.mark.asyncio
async def test_user_can_modify_own_resources(auth_backend):
    user = {"user_id": "user-1", "role": "user"}
    assert await auth_backend.authorize(user, "graph", "invoke") == True
    assert await auth_backend.authorize(user, "checkpointer", "write", "thread-1") == True
```

### Integration Testing

```python
from fastapi.testclient import TestClient
from my_agent.main import app

client = TestClient(app)

def test_authorized_access():
    response = client.post(
        "/v1/graph/invoke",
        headers={"Authorization": "Bearer admin-token"},
        json={"messages": [{"role": "user", "content": "test"}]}
    )
    assert response.status_code == 200

def test_unauthorized_access():
    response = client.post(
        "/v1/graph/stop",
        headers={"Authorization": "Bearer viewer-token"},
        json={"thread_id": "123"}
    )
    assert response.status_code == 403
    assert "Not authorized" in response.json()["error"]["message"]
```

## Troubleshooting

### Authorization Always Returns 403

**Problem**: All requests return 403 Forbidden

**Solutions**:
1. Check that your authorization backend is properly configured in `agentflow.json`
2. Verify the module path is correct: `"module.path:attribute_name"`
3. Ensure your `authorize()` method returns `True` for the expected cases
4. Add logging to see what values are being passed to `authorize()`
5. Check that the user object has the expected fields (e.g., `user_id`, `role`)

```python
# Add debug logging
async def authorize(self, user, resource, action, resource_id=None, **context):
    print(f"DEBUG: user={user}, resource={resource}, action={action}")
    # Your logic here
```

### Authorization Not Being Called

**Problem**: Authorization backend never gets invoked

**Solutions**:
1. Verify `authorization` is set in `agentflow.json`
2. Check that the file path exists and is importable
3. Ensure the attribute name matches the variable name in your module
4. Restart the API server after configuration changes

### Performance Issues

**Problem**: Authorization checks are slow

**Solutions**:
1. Implement caching for expensive operations (database queries, API calls)
2. Use Redis for distributed caching in production
3. Minimize external API calls in authorization logic
4. Consider pre-computing permissions and storing them with the user
5. Use async operations properly (don't block with sync calls)

## Security Considerations

### 1. Never Trust User Input

Always validate user-provided data in authorization logic:

```python
async def authorize(self, user, resource, action, resource_id=None, **context):
    # ✅ Good: Validate inputs
    if not user or not user.get("user_id"):
        return False
    
    # ❌ Bad: Trusting user-provided role
    # The role should come from your database, not the token
    if user.get("role") == "admin":  # What if user modified their token?
        return True
```

### 2. Keep Authorization Logic Server-Side

Never implement authorization checks in client-side code - they can be bypassed.

### 3. Use the Principle of Least Privilege

Grant users the minimum permissions they need:

```python
# ✅ Good: Specific permissions
if action == "read" and resource == "checkpointer":
    return True

# ❌ Bad: Overly permissive
return True  # Everyone can do everything
```

### 4. Audit Authorization Decisions

Log authorization decisions for security audits:

```python
async def authorize(self, user, resource, action, resource_id=None, **context):
    decision = self._make_decision(user, resource, action, resource_id)
    
    # Log to audit trail
    await self.audit_log.record({
        "timestamp": datetime.now(),
        "user_id": user.get("user_id"),
        "resource": resource,
        "action": action,
        "resource_id": resource_id,
        "decision": "allow" if decision else "deny"
    })
    
    return decision
```

## Production Checklist

Before deploying to production, ensure:

- [ ] Custom authorization backend is implemented and tested
- [ ] Authorization is configured in `agentflow.json`
- [ ] All expected user roles/permissions are defined
- [ ] Authorization decisions are logged for audit
- [ ] Performance testing completed (especially for expensive checks)
- [ ] Edge cases are handled (missing user_id, null values, etc.)
- [ ] Fail-secure pattern is implemented (deny by default)
- [ ] Sensitive data is not logged (use log sanitization)
- [ ] Rate limiting is considered for API abuse prevention
- [ ] Backup authorization mechanism exists (if primary fails)

## Additional Resources

- [Authentication Guide](authentication.md) - Set up user authentication
- [Configuration Guide](configuration.md) - Configure your AgentFlow application
- [Deployment Guide](deployment.md) - Deploy securely to production
- [Security Review](../SECURITY_REVIEW.md) - Framework security analysis
- [Security Action Plan](../SECURITY_ACTION_PLAN.md) - Security improvement roadmap

## Examples Repository

Complete authorization examples are available in the `examples/authorization/` directory:

- `examples/authorization/rbac.py` - Role-based access control
- `examples/authorization/abac.py` - Attribute-based access control
- `examples/authorization/ownership.py` - Owner-based access control
- `examples/authorization/tier_based.py` - API tier-based access control

## Support

If you have questions about implementing authorization:

1. Check the [FAQ section](#faq) below
2. Review the example implementations in `examples/authorization/`
3. Open an issue on GitHub with the `authorization` label
4. Join our community Discord for real-time help

## FAQ

**Q: Can I have multiple authorization backends?**

A: Not directly, but you can create a composite backend that delegates to multiple backends:

```python
class CompositeAuthBackend(AuthorizationBackend):
    def __init__(self, backends: list[AuthorizationBackend]):
        self.backends = backends
    
    async def authorize(self, user, resource, action, resource_id=None, **context):
        # All backends must approve
        for backend in self.backends:
            if not await backend.authorize(user, resource, action, resource_id, **context):
                return False
        return True

authorization_backend = CompositeAuthBackend([
    RBACBackend(),
    RateLimitBackend(),
    OwnershipBackend()
])
```

**Q: Can I disable authorization for development?**

A: Yes, simply don't configure the `authorization` field in `agentflow.json`. The framework will use `DefaultAuthorizationBackend` which allows all authenticated users.

**Q: How do I handle anonymous access?**

A: Authorization only runs for authenticated requests. If you want to allow some endpoints without authentication, you'll need to modify your authentication backend to return a default user for unauthenticated requests.

**Q: Can authorization decisions be async?**

A: Yes! The `authorize()` method is async, so you can make database queries, API calls, or any async operation:

```python
async def authorize(self, user, resource, action, resource_id=None, **context):
    # Async database query
    permissions = await self.db.get_user_permissions(user["user_id"])
    return action in permissions
```

**Q: What's the performance impact of authorization?**

A: Minimal if implemented correctly. Simple checks (role comparison) add <1ms. Database queries should be cached. For complex logic, use caching with TTL.

**Q: Can I use the request object in authorization?**

A: The request object is not directly passed, but you can access context via the `**context` parameter. For example, the graph input is passed as `input=graph_input` in graph authorization calls.
